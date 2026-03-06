from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session

from ..models.project_log import ProjectLog


def create_project_log(
    db: Session,
    *,
    project_id: str,
    message: str,
    level: str,
    source: str,
) -> ProjectLog:
    entry = ProjectLog(
        project_id=project_id,
        level=level.upper(),
        source=source,
        message=message[:4000],
        created_at=datetime.utcnow(),
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry


def trim_project_logs(db: Session, *, project_id: str, max_entries: int) -> None:
    total = db.query(ProjectLog).filter_by(project_id=project_id).count()
    if total <= max_entries:
        return

    excess = total - max_entries
    oldest_ids = (
        db.query(ProjectLog.id)
        .filter_by(project_id=project_id)
        .order_by(ProjectLog.created_at.asc())
        .limit(excess)
        .all()
    )
    if oldest_ids:
        ids = [row[0] for row in oldest_ids]
        db.query(ProjectLog).filter(ProjectLog.id.in_(ids)).delete(synchronize_session=False)
        db.commit()


def list_project_logs(
    db: Session,
    *,
    project_id: str,
    level: Optional[str],
    limit: int,
    offset: int,
) -> list[ProjectLog]:
    query = db.query(ProjectLog).filter_by(project_id=project_id)
    if level:
        query = query.filter(ProjectLog.level == level.upper())
    return (
        query.order_by(ProjectLog.created_at.desc())
        .offset(offset)
        .limit(min(limit, 200))
        .all()
    )


def count_project_logs(db: Session, *, project_id: str, level: Optional[str]) -> int:
    query = db.query(ProjectLog).filter_by(project_id=project_id)
    if level:
        query = query.filter(ProjectLog.level == level.upper())
    return query.count()
