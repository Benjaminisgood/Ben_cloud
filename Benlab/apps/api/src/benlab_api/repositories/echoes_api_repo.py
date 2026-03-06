from __future__ import annotations

from sqlalchemy import or_, select
from sqlalchemy.orm import Session, selectinload

from benlab_api.models import Attachment, Message


def list_echo_records(
    db: Session,
    *,
    viewer_user_id: int,
    is_admin: bool,
    before_id: int | None,
    limit: int,
) -> list[Message]:
    stmt = select(Message).options(selectinload(Message.sender))
    if not is_admin:
        stmt = stmt.where(or_(Message.sender_id == viewer_user_id, Message.receiver_id == viewer_user_id))
    if before_id:
        stmt = stmt.where(Message.id < before_id)
    stmt = stmt.order_by(Message.id.desc()).limit(limit + 1)
    return db.scalars(stmt).all()


def list_echo_assets(
    db: Session,
    *,
    before_asset_id: int | None,
    limit: int,
) -> list[Attachment]:
    stmt = select(Attachment)
    if before_asset_id:
        stmt = stmt.where(Attachment.id < before_asset_id)
    stmt = stmt.order_by(Attachment.id.desc()).limit(limit + 1)
    return db.scalars(stmt).all()
