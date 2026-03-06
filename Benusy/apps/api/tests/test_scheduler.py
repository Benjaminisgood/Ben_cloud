from __future__ import annotations

import asyncio

from sqlmodel import Session

from benusy_api.db.database import engine
from benusy_api.models import Assignment, AssignmentStatus, MetricSyncStatus
from benusy_api.services import scheduler as scheduler_service


def test_metrics_update_cycle_fallbacks_to_manual_required_on_sync_error(client, monkeypatch):
    with Session(engine) as session:
        assignment = Assignment(
            task_id=1,
            user_id=1,
            status=AssignmentStatus.in_review,
            post_link="http://example.com/post/1",
            metric_sync_status=MetricSyncStatus.normal,
        )
        session.add(assignment)
        session.commit()
        session.refresh(assignment)
        assignment_id = assignment.id

    async def _broken_sync(_session, _assignment):
        raise RuntimeError("mock sync boom")

    monkeypatch.setattr(scheduler_service, "sync_assignment_metrics_once", _broken_sync)

    asyncio.run(scheduler_service.run_metrics_update_cycle())

    with Session(engine) as session:
        updated = session.get(Assignment, assignment_id)
        assert updated is not None
        assert updated.metric_sync_status == MetricSyncStatus.manual_required
        assert updated.last_sync_error is not None
        assert "mock sync boom" in updated.last_sync_error
