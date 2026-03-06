from __future__ import annotations

from sqlalchemy import desc, func
from sqlalchemy.orm import Session

from ..models import GeneratedAsset, Record, Tag, User


def list_public_records(db: Session, *, limit: int) -> list[Record]:
    return (
        db.query(Record)
        .filter(Record.visibility == "public")
        .order_by(desc(Record.id))
        .limit(limit)
        .all()
    )


def list_public_digest_assets(db: Session, *, limit: int) -> list[GeneratedAsset]:
    return (
        db.query(GeneratedAsset)
        .filter(
            GeneratedAsset.visibility == "public",
            GeneratedAsset.is_daily_digest.is_(True),
            GeneratedAsset.status == "ready",
        )
        .order_by(desc(GeneratedAsset.id))
        .limit(limit)
        .all()
    )


def count_public_records(db: Session) -> int:
    return db.query(func.count(Record.id)).filter(Record.visibility == "public").scalar() or 0


def count_users(db: Session) -> int:
    return db.query(func.count(User.id)).scalar() or 0


def list_top_public_tags(db: Session, *, limit: int):
    return (
        db.query(Tag.name, func.count(Tag.name).label("count"))
        .join(Record.tags)
        .filter(Record.visibility == "public")
        .group_by(Tag.name)
        .order_by(desc("count"))
        .limit(limit)
        .all()
    )
