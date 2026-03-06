from __future__ import annotations

import re
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy.orm import Session, joinedload

from ..models import Comment, Content, Record, Tag
from ..services.records_service import VALID_VISIBILITY, visible_filter

_DATE_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def _base_visible_records_query(db: Session, viewer_id: int):
    return (
        db.query(Record)
        .options(joinedload(Record.user), joinedload(Record.content))
        .filter(visible_filter(viewer_id))
    )


def list_records(
    db: Session,
    *,
    viewer_id: int,
    user_id: Optional[int] = None,
    tag: str = "",
    day: str = "",
    visibility: str = "",
    before_id: Optional[int] = None,
    limit: int = 40,
) -> tuple[list[Record], bool]:
    q = _base_visible_records_query(db, viewer_id)
    if user_id is not None:
        q = q.filter(Record.user_id == user_id)
    if tag:
        q = q.filter(Record.tags.any(Tag.name_norm == tag.lower()))
    if day and _DATE_PATTERN.match(day):
        start = datetime.strptime(day, "%Y-%m-%d")
        end = start + timedelta(days=1)
        q = q.filter(Record.created_at >= start, Record.created_at < end)
    if visibility in VALID_VISIBILITY:
        q = q.filter(Record.visibility == visibility)
    if before_id:
        q = q.filter(Record.id < before_id)
    rows = q.order_by(Record.id.desc()).limit(limit + 1).all()
    return rows[:limit], len(rows) > limit


def pull_records(
    db: Session,
    *,
    viewer_id: int,
    user_id: Optional[int] = None,
    tag: str = "",
    before_id: Optional[int] = None,
    limit: int = 40,
) -> tuple[list[Record], bool]:
    q = _base_visible_records_query(db, viewer_id)
    if user_id is not None:
        q = q.filter(Record.user_id == user_id)
    if tag:
        q = q.filter(Record.tags.any(Tag.name_norm == tag.lower()))
    if before_id:
        q = q.filter(Record.id < before_id)
    rows = q.order_by(Record.id.desc()).limit(limit + 1).all()
    return rows[:limit], len(rows) > limit


def get_record_detail(db: Session, record_id: int) -> Record | None:
    return (
        db.query(Record)
        .options(joinedload(Record.user), joinedload(Record.content))
        .filter(Record.id == record_id)
        .first()
    )


def get_record_by_content_id(db: Session, content_id: int) -> Record | None:
    return db.query(Record).filter_by(content_id=content_id).first()


def list_comments(db: Session, *, record_id: int) -> list[Comment]:
    return (
        db.query(Comment)
        .options(joinedload(Comment.user))
        .filter_by(record_id=record_id)
        .order_by(Comment.created_at.asc())
        .all()
    )


def search_tags(db: Session, *, q: str, limit: int) -> list[Tag]:
    query = db.query(Tag)
    if q:
        query = query.filter(Tag.name_norm.like(f"{q.lower()}%"))
    return query.order_by(Tag.name_norm.asc()).limit(limit).all()


def get_content(db: Session, content_id: int) -> Content | None:
    return db.get(Content, content_id)

