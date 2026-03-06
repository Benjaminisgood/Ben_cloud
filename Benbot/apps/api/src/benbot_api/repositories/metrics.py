from __future__ import annotations

from sqlalchemy import func
from sqlalchemy.orm import Session

from ..models import BugReport, ProjectLog, User
from .project_stats import list_project_health_rows


def list_health_rows(db: Session):
    return list_project_health_rows(db)


def list_project_log_counts(db: Session) -> list[tuple[str, str, int]]:
    return (
        db.query(ProjectLog.project_id, ProjectLog.level, func.count(ProjectLog.id))
        .group_by(ProjectLog.project_id, ProjectLog.level)
        .all()
    )


def list_bug_report_counts_by_status(db: Session) -> list[tuple[str, int]]:
    return (
        db.query(BugReport.status, func.count(BugReport.id))
        .group_by(BugReport.status)
        .all()
    )


def count_users(db: Session) -> int:
    return db.query(func.count(User.id)).scalar() or 0
