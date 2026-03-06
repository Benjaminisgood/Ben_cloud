from __future__ import annotations

from sqlalchemy.orm import Session

from ..models.bug_report import BugReport
from ..models.user import User


def create_bug_report(db: Session, *, reporter_id: int, body: str) -> BugReport:
    bug = BugReport(reporter_id=reporter_id, body=body.strip())
    db.add(bug)
    db.commit()
    db.refresh(bug)
    return bug


def get_bug_report(db: Session, bug_id: int) -> BugReport | None:
    return db.get(BugReport, bug_id)


def save_bug_report(db: Session, bug: BugReport) -> BugReport:
    db.add(bug)
    db.commit()
    db.refresh(bug)
    return bug


def list_pending_bug_reports_with_reporter(db: Session) -> list[tuple[BugReport, str]]:
    return (
        db.query(BugReport, User.username)
        .join(User, BugReport.reporter_id == User.id)
        .filter(BugReport.status == "pending")
        .order_by(BugReport.created_at.asc())
        .all()
    )


def list_approved_bug_reports_with_reporter(db: Session) -> list[tuple[BugReport, str]]:
    return (
        db.query(BugReport, User.username)
        .join(User, BugReport.reporter_id == User.id)
        .filter(BugReport.status == "approved")
        .order_by(BugReport.approved_at.desc())
        .all()
    )


def list_approved_bug_reports(db: Session) -> list[BugReport]:
    return (
        db.query(BugReport)
        .filter(BugReport.status == "approved")
        .order_by(BugReport.approved_at.asc())
        .all()
    )
