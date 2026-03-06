from __future__ import annotations

from datetime import datetime

from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from ..models import Record, Tag, User


def visible_filter(viewer_user_id: int):
    return or_(Record.visibility == "public", Record.user_id == viewer_user_id)


def list_heat_rows(
    db: Session,
    *,
    viewer_user_id: int,
    start_at: datetime,
    tag_norm: str = "",
):
    query = (
        db.query(
            Record.user_id,
            func.date(Record.created_at).label("day"),
            func.count(Record.id).label("cnt"),
        )
        .filter(visible_filter(viewer_user_id), Record.created_at >= start_at)
    )
    if tag_norm:
        query = query.filter(Record.tags.any(Tag.name_norm == tag_norm))
    return query.group_by(Record.user_id, func.date(Record.created_at)).all()


def list_users_by_ids(db: Session, *, user_ids: list[int]) -> list[User]:
    if not user_ids:
        return []
    return db.query(User).filter(User.id.in_(user_ids)).all()


def list_top_tags(
    db: Session,
    *,
    viewer_user_id: int,
    limit: int,
    start_at: datetime | None = None,
):
    query = (
        db.query(Tag.name, func.count(Record.id).label("cnt"))
        .join(Record.tags)
        .filter(visible_filter(viewer_user_id))
    )
    if start_at is not None:
        query = query.filter(Record.created_at >= start_at)
    return query.group_by(Tag.name).order_by(func.count(Record.id).desc()).limit(limit).all()


def list_records_in_user_day(
    db: Session,
    *,
    viewer_user_id: int,
    user_id: int,
    start_at: datetime,
    end_at: datetime,
) -> list[Record]:
    return (
        db.query(Record)
        .filter(
            visible_filter(viewer_user_id),
            Record.user_id == user_id,
            Record.created_at >= start_at,
            Record.created_at < end_at,
        )
        .order_by(Record.created_at.desc())
        .all()
    )


def list_user_records(
    db: Session,
    *,
    viewer_user_id: int,
    user_id: int,
    before_id: int,
    limit: int,
) -> list[Record]:
    query = db.query(Record).filter(visible_filter(viewer_user_id), Record.user_id == user_id)
    if before_id:
        query = query.filter(Record.id < before_id)
    return query.order_by(Record.id.desc()).limit(limit + 1).all()


def list_date_records(
    db: Session,
    *,
    viewer_user_id: int,
    start_at: datetime,
    end_at: datetime,
    before_id: int,
    limit: int,
) -> list[Record]:
    query = db.query(Record).filter(
        visible_filter(viewer_user_id),
        Record.created_at >= start_at,
        Record.created_at < end_at,
    )
    if before_id:
        query = query.filter(Record.id < before_id)
    return query.order_by(Record.id.desc()).limit(limit + 1).all()
