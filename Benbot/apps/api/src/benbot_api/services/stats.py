"""Click statistics for sub-projects."""
from __future__ import annotations

from sqlalchemy.orm import Session

from ..repositories import (
    get_all_project_total_clicks,
    get_project_total_clicks,
    increment_project_click,
)


def record_click(db: Session, project_id: str) -> None:
    """Increment today's click count for a project."""
    increment_project_click(db, project_id)


def get_total_clicks(db: Session, project_id: str) -> int:
    """Return total click count for a project across all dates."""
    return get_project_total_clicks(db, project_id)


def get_all_total_clicks(db: Session) -> dict[str, int]:
    return get_all_project_total_clicks(db)
