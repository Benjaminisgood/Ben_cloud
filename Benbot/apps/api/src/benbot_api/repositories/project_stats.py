from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import func
from sqlalchemy.orm import Session

from ..models import ProjectClick, ProjectHealth


def increment_project_click(db: Session, project_id: str, *, on_date: date | None = None) -> None:
    click_date = on_date or date.today()
    row = (
        db.query(ProjectClick)
        .filter_by(project_id=project_id, click_date=click_date)
        .first()
    )
    if row is None:
        row = ProjectClick(project_id=project_id, click_date=click_date, count=0)
        db.add(row)
    row.count += 1
    db.commit()


def get_project_total_clicks(db: Session, project_id: str) -> int:
    result = db.query(func.sum(ProjectClick.count)).filter_by(project_id=project_id).scalar()
    return result or 0


def get_all_project_total_clicks(db: Session) -> dict[str, int]:
    rows = (
        db.query(ProjectClick.project_id, func.sum(ProjectClick.count))
        .group_by(ProjectClick.project_id)
        .all()
    )
    return {project_id: total for project_id, total in rows}


def list_project_health_rows(db: Session) -> list[ProjectHealth]:
    return db.query(ProjectHealth).all()


def get_project_health_map(db: Session) -> dict[str, ProjectHealth]:
    return {row.project_id: row for row in list_project_health_rows(db)}


def upsert_project_health(
    db: Session,
    *,
    existing: ProjectHealth | None,
    project_id: str,
    status: str,
    response_ms: int | None,
    checked_at: datetime | None = None,
) -> ProjectHealth:
    row = existing
    if row is None:
        row = ProjectHealth(project_id=project_id)
        db.add(row)
    row.status = status
    row.response_ms = response_ms
    row.last_checked = checked_at or datetime.utcnow()
    db.commit()
    db.refresh(row)
    return row
