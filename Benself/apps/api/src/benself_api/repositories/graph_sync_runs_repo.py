from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from benself_api.models import GraphSyncRun


def list_graph_sync_runs(db: Session, *, limit: int = 20) -> list[GraphSyncRun]:
    stmt = select(GraphSyncRun).order_by(GraphSyncRun.created_at.desc()).limit(limit)
    return list(db.execute(stmt).scalars().all())


def create_graph_sync_run(
    db: Session,
    *,
    mode: str,
    status: str,
    raw_episode_count: int,
    confirmed_episode_count: int,
    backend: str,
    message: str,
    created_by: str,
) -> GraphSyncRun:
    item = GraphSyncRun(
        mode=mode,
        status=status,
        raw_episode_count=raw_episode_count,
        confirmed_episode_count=confirmed_episode_count,
        backend=backend,
        message=message,
        created_by=created_by,
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return item
