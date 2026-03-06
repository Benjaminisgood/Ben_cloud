from __future__ import annotations

from datetime import date, datetime, time, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from benlab_api.models import Attachment


def _day_bounds(value: date) -> tuple[datetime, datetime]:
    start = datetime.combine(value, time.min)
    return start, start + timedelta(days=1)


def list_ready_generated_assets(
    db: Session,
    *,
    kind: str,
    source_day: date | None,
    is_daily_digest: bool | None,
    before_id: int | None,
    limit: int,
) -> list[Attachment]:
    if kind and kind != "attachment":
        return []

    stmt = select(Attachment)
    if source_day is not None:
        start, end = _day_bounds(source_day)
        stmt = stmt.where(Attachment.created_at >= start, Attachment.created_at < end)

    if is_daily_digest is True:
        stmt = stmt.where(Attachment.filename.ilike("%digest%"))
    elif is_daily_digest is False:
        stmt = stmt.where(~Attachment.filename.ilike("%digest%"))

    if before_id:
        stmt = stmt.where(Attachment.id < before_id)
    stmt = stmt.order_by(Attachment.id.desc()).limit(limit + 1)
    return db.scalars(stmt).all()


def get_generated_asset(db: Session, *, asset_id: int) -> Attachment | None:
    return db.get(Attachment, asset_id)
