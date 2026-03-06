from __future__ import annotations

from datetime import datetime

from sqlalchemy import and_, or_
from sqlalchemy.orm import Session, joinedload

from ..models import GeneratedAsset, Record


def _visible_record_filter(viewer_user_id: int, *, include_private: bool):
    if include_private:
        return or_(Record.visibility == "public", Record.user_id == viewer_user_id)
    return Record.visibility == "public"


def _visible_asset_filter(viewer_user_id: int, *, include_private: bool):
    if include_private:
        return or_(GeneratedAsset.visibility == "public", GeneratedAsset.user_id == viewer_user_id)
    return GeneratedAsset.visibility == "public"


def list_echo_records(
    db: Session,
    *,
    viewer_user_id: int,
    include_private: bool,
    cursor_time: datetime | None,
    cursor_id: int | None,
    cursor_kind: str,
    limit: int,
) -> list[Record]:
    query = (
        db.query(Record)
        .options(joinedload(Record.user), joinedload(Record.content))
        .filter(_visible_record_filter(viewer_user_id, include_private=include_private))
    )
    if cursor_time is not None:
        if cursor_kind == "record" and cursor_id:
            query = query.filter(
                or_(
                    Record.created_at < cursor_time,
                    and_(Record.created_at == cursor_time, Record.id < cursor_id),
                )
            )
        else:
            query = query.filter(Record.created_at <= cursor_time)
    return query.order_by(Record.created_at.desc(), Record.id.desc()).limit(limit + 1).all()


def list_echo_assets(
    db: Session,
    *,
    viewer_user_id: int,
    include_private: bool,
    cursor_time: datetime | None,
    cursor_id: int | None,
    cursor_kind: str,
    limit: int,
) -> list[GeneratedAsset]:
    query = db.query(GeneratedAsset).filter(
        _visible_asset_filter(viewer_user_id, include_private=include_private),
        GeneratedAsset.status == "ready",
    )
    if cursor_time is not None:
        if cursor_kind == "asset" and cursor_id:
            query = query.filter(
                or_(
                    GeneratedAsset.created_at < cursor_time,
                    and_(GeneratedAsset.created_at == cursor_time, GeneratedAsset.id < cursor_id),
                )
            )
        else:
            query = query.filter(GeneratedAsset.created_at <= cursor_time)
    return query.order_by(GeneratedAsset.created_at.desc(), GeneratedAsset.id.desc()).limit(limit + 1).all()
