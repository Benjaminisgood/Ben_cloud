from __future__ import annotations

import re
from collections import Counter
from datetime import date, datetime

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, selectinload

from benlab_api.models import Member, Message

_TAG_PATTERN = re.compile(r"#([A-Za-z0-9_\-\u4e00-\u9fff]+)")


def _base_visible_stmt(*, viewer_user_id: int, is_admin: bool):
    stmt = select(Message).options(selectinload(Message.sender))
    if is_admin:
        return stmt
    return stmt.where(or_(Message.sender_id == viewer_user_id, Message.receiver_id == viewer_user_id))


def list_heat_rows(db: Session, *, viewer_user_id: int, is_admin: bool, start_at: datetime):
    day_col = func.date(Message.timestamp)
    stmt = select(
        Message.sender_id.label("user_id"),
        day_col.label("day"),
        func.count(Message.id).label("cnt"),
    ).where(Message.timestamp >= start_at)
    if not is_admin:
        stmt = stmt.where(or_(Message.sender_id == viewer_user_id, Message.receiver_id == viewer_user_id))
    stmt = stmt.group_by(Message.sender_id, day_col)
    return db.execute(stmt).all()


def latest_visible_message_day(db: Session, *, viewer_user_id: int, is_admin: bool) -> date | None:
    stmt = select(func.max(Message.timestamp))
    if not is_admin:
        stmt = stmt.where(or_(Message.sender_id == viewer_user_id, Message.receiver_id == viewer_user_id))
    ts = db.scalar(stmt)
    if ts is None:
        return None
    return ts.date()


def list_users_by_ids(db: Session, *, user_ids: list[int]) -> list[Member]:
    if not user_ids:
        return []
    return db.scalars(select(Member).where(Member.id.in_(user_ids))).all()


def list_top_tags(
    db: Session,
    *,
    viewer_user_id: int,
    is_admin: bool,
    limit: int,
    start_at: datetime | None = None,
) -> list[tuple[str, int]]:
    stmt = select(Message.content)
    if start_at is not None:
        stmt = stmt.where(Message.timestamp >= start_at)
    if not is_admin:
        stmt = stmt.where(or_(Message.sender_id == viewer_user_id, Message.receiver_id == viewer_user_id))

    rows = db.scalars(stmt.order_by(Message.id.desc()).limit(3000)).all()
    counter: Counter[str] = Counter()
    for content in rows:
        for tag in _TAG_PATTERN.findall(str(content or "")):
            counter[tag] += 1
    return counter.most_common(limit)


def list_records_in_user_day(
    db: Session,
    *,
    viewer_user_id: int,
    is_admin: bool,
    user_id: int,
    start_at: datetime,
    end_at: datetime,
) -> list[Message]:
    stmt = _base_visible_stmt(viewer_user_id=viewer_user_id, is_admin=is_admin).where(
        Message.sender_id == user_id,
        Message.timestamp >= start_at,
        Message.timestamp < end_at,
    )
    stmt = stmt.order_by(Message.timestamp.desc(), Message.id.desc())
    return db.scalars(stmt).all()


def list_user_records(
    db: Session,
    *,
    viewer_user_id: int,
    is_admin: bool,
    user_id: int,
    before_id: int,
    limit: int,
) -> list[Message]:
    stmt = _base_visible_stmt(viewer_user_id=viewer_user_id, is_admin=is_admin).where(Message.sender_id == user_id)
    if before_id:
        stmt = stmt.where(Message.id < before_id)
    stmt = stmt.order_by(Message.id.desc()).limit(limit + 1)
    return db.scalars(stmt).all()


def list_date_records(
    db: Session,
    *,
    viewer_user_id: int,
    is_admin: bool,
    start_at: datetime,
    end_at: datetime,
    before_id: int,
    limit: int,
) -> list[Message]:
    stmt = _base_visible_stmt(viewer_user_id=viewer_user_id, is_admin=is_admin).where(
        Message.timestamp >= start_at,
        Message.timestamp < end_at,
    )
    if before_id:
        stmt = stmt.where(Message.id < before_id)
    stmt = stmt.order_by(Message.id.desc()).limit(limit + 1)
    return db.scalars(stmt).all()
