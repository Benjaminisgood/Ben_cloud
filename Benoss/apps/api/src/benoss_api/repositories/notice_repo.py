from __future__ import annotations

from datetime import datetime

from sqlalchemy import or_
from sqlalchemy.orm import Session, joinedload

from ..models import Record, Tag


def visible_filter(viewer_user_id: int):
    return or_(Record.visibility == "public", Record.user_id == viewer_user_id)


def _base_query(db: Session, *, viewer_user_id: int):
    return (
        db.query(Record)
        .options(joinedload(Record.user), joinedload(Record.content))
        .filter(visible_filter(viewer_user_id))
    )


def _apply_common_filters(
    query,
    *,
    user_id: int | None,
    tag: str,
    day_start: datetime | None,
    day_end: datetime | None,
    before_id: int | None,
):
    if user_id is not None:
        query = query.filter(Record.user_id == user_id)
    if tag:
        query = query.filter(Record.tags.any(Tag.name_norm == tag.lower()))
    if day_start is not None and day_end is not None:
        query = query.filter(Record.created_at >= day_start, Record.created_at < day_end)
    if before_id:
        query = query.filter(Record.id < before_id)
    return query


def list_notice_records(
    db: Session,
    *,
    viewer_user_id: int,
    user_id: int | None,
    tag: str,
    day_start: datetime | None,
    day_end: datetime | None,
    before_id: int | None,
    limit: int,
):
    query = _base_query(db, viewer_user_id=viewer_user_id)
    query = _apply_common_filters(
        query,
        user_id=user_id,
        tag=tag,
        day_start=day_start,
        day_end=day_end,
        before_id=before_id,
    )
    return query.order_by(Record.id.desc()).limit(limit + 1).all()


def list_notice_render_records(
    db: Session,
    *,
    viewer_user_id: int,
    user_id: int | None,
    tag: str,
    day_start: datetime | None,
    day_end: datetime | None,
    order: str,
    limit: int,
):
    query = _base_query(db, viewer_user_id=viewer_user_id)
    query = _apply_common_filters(
        query,
        user_id=user_id,
        tag=tag,
        day_start=day_start,
        day_end=day_end,
        before_id=None,
    )
    if order == "asc":
        query = query.order_by(Record.id.asc())
    else:
        query = query.order_by(Record.id.desc())
    return query.limit(limit).all()
