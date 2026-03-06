import asyncio
import logging
from datetime import datetime

from sqlmodel import Session, select

from benusy_api.core.config import settings
from benusy_api.db.database import engine
from benusy_api.models import Assignment, AssignmentStatus, MetricSyncStatus
from benusy_api.services.sync import sync_assignment_metrics_once

logger = logging.getLogger(__name__)


def _mark_sync_failure(assignment: Assignment, exc: Exception) -> None:
    assignment.metric_sync_status = MetricSyncStatus.manual_required
    assignment.last_sync_error = f"Scheduler sync failed: {exc}"
    assignment.updated_at = datetime.utcnow()


async def run_metrics_update_cycle() -> int:
    with Session(engine) as session:
        assignments = session.exec(
            select(Assignment).where(
                Assignment.status == AssignmentStatus.in_review,
                Assignment.metric_sync_status.in_([
                    MetricSyncStatus.normal,
                    MetricSyncStatus.manual_required,
                ]),
            )
        ).all()

        for assignment in assignments:
            try:
                await sync_assignment_metrics_once(session, assignment)
            except Exception as exc:
                logger.exception(
                    "Metrics sync failed for assignment_id=%s, fallback to manual review",
                    assignment.id,
                )
                _mark_sync_failure(assignment, exc)

        session.commit()
        return len(assignments)


async def metrics_update_loop(stop_event: asyncio.Event) -> None:
    interval = settings.metrics_update_interval_seconds
    if interval <= 0:
        logger.info("Metrics scheduler disabled (interval=%s)", interval)
        return

    while not stop_event.is_set():
        try:
            await run_metrics_update_cycle()
            try:
                await asyncio.wait_for(stop_event.wait(), timeout=interval)
            except asyncio.TimeoutError:
                continue
        except asyncio.CancelledError:
            return
        except Exception:
            logger.exception("Metrics scheduler loop crashed, will retry after interval=%s", interval)
            try:
                await asyncio.wait_for(stop_event.wait(), timeout=interval)
            except asyncio.TimeoutError:
                continue
