from __future__ import annotations

from datetime import date

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from benjournal_api.models import JournalDay


def get_day_by_date(db: Session, *, entry_date: date) -> JournalDay | None:
    stmt = select(JournalDay).where(JournalDay.entry_date == entry_date)
    return db.execute(stmt).scalar_one_or_none()


def create_day(db: Session, *, entry_date: date, username: str) -> JournalDay:
    item = JournalDay(
        entry_date=entry_date,
        created_by=username,
        updated_by=username,
        storage_provider="local",
        storage_status="pending",
        transcript_status="pending",
    )
    db.add(item)
    db.flush()
    return item


def list_recent_days(db: Session, *, limit: int = 14) -> list[JournalDay]:
    stmt = select(JournalDay).order_by(JournalDay.entry_date.desc()).limit(limit)
    return list(db.execute(stmt).scalars().all())


def get_day_totals(db: Session) -> tuple[int, int]:
    stmt = select(
        func.count(JournalDay.id),
        func.coalesce(func.sum(JournalDay.segment_count), 0),
    )
    count, segments = db.execute(stmt).one()
    return int(count or 0), int(segments or 0)
