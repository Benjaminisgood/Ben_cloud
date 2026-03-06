"""Background health-check service for sub-projects."""
from __future__ import annotations

import asyncio
import logging
import time
from datetime import datetime

import httpx
from sqlalchemy.orm import Session

from ..core.config import ProjectConfig, get_settings
from ..db.session import SessionLocal
from ..models import ProjectHealth
from ..repositories import (
    get_project_health_map,
    upsert_project_health,
)
from .logs import add_log
from .metrics import inc_counter

logger = logging.getLogger(__name__)


def _upsert_health(
    db: Session,
    row: ProjectHealth | None,
    project_id: str,
    status: str,
    response_ms: int | None,
) -> ProjectHealth:
    return upsert_project_health(
        db,
        existing=row,
        project_id=project_id,
        status=status,
        response_ms=response_ms,
        checked_at=datetime.utcnow(),
    )


async def check_one(project: ProjectConfig) -> tuple[str, int | None]:
    start = time.monotonic()
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(f"{project.internal_url}/health")
            ms = int((time.monotonic() - start) * 1000)
            if resp.status_code == 200:
                return "up", ms
            return "down", ms
    except Exception:
        return "down", None


async def run_health_checks() -> None:
    """Run a single round of health checks for all projects."""
    inc_counter("benbot_health_check_runs_total")
    settings = get_settings()
    projects = settings.get_projects()
    results = await asyncio.gather(*[check_one(p) for p in projects], return_exceptions=True)
    with SessionLocal() as db:
        existing_rows = get_project_health_map(db)
        for project, result in zip(projects, results):
            previous = existing_rows.get(project.id)
            previous_status = previous.status if previous else "unknown"
            if isinstance(result, Exception):
                status, ms = "down", None
                logger.warning("Health check exception for %s: %s", project.id, result)
            else:
                status, ms = result
            if status == "down":
                inc_counter("benbot_health_check_failures_total")
                if previous_status != "down":
                    msg = (
                        f"健康检查状态变化: {previous_status} -> down "
                        f"(响应时间: {'超时' if ms is None else f'{ms}ms'})"
                    )
                    logger.warning("Health %s transitioned to down", project.id)
                    add_log(db, project.id, msg, level="ERROR", source="health_check")
            elif previous_status != "up":
                msg = (
                    f"健康检查状态变化: {previous_status} -> up "
                    f"({ms if ms is not None else '-'}ms)"
                )
                logger.info("Health %s recovered to up (%sms)", project.id, ms)
                add_log(db, project.id, msg, level="INFO", source="health_check")

            updated = _upsert_health(db, previous, project.id, status, ms)
            existing_rows[project.id] = updated


async def health_check_loop() -> None:
    """Infinite loop for periodic health checks."""
    settings = get_settings()
    interval = settings.HEALTH_CHECK_INTERVAL
    while True:
        try:
            await run_health_checks()
        except Exception:
            logger.exception("Health check loop error")
        await asyncio.sleep(interval)


def get_all_health(db: Session) -> dict[str, ProjectHealth]:
    return get_project_health_map(db)
