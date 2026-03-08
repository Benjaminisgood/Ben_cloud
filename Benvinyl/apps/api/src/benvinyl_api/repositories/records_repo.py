from __future__ import annotations

from datetime import date

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..models import VinylRecord


def list_records(db: Session) -> list[VinylRecord]:
    stmt = select(VinylRecord).order_by(VinylRecord.created_at.desc(), VinylRecord.id.desc())
    return list(db.scalars(stmt))


def get_record_by_id(db: Session, record_id: int) -> VinylRecord | None:
    stmt = select(VinylRecord).where(VinylRecord.id == record_id)
    return db.scalar(stmt)


def get_record_by_oss_path(db: Session, oss_path: str) -> VinylRecord | None:
    stmt = select(VinylRecord).where(VinylRecord.oss_path == oss_path)
    return db.scalar(stmt)


def list_selected_records(db: Session, *, display_date: date, include_trashed: bool) -> list[VinylRecord]:
    stmt = select(VinylRecord).where(VinylRecord.selected_for_date == display_date)
    if not include_trashed:
        stmt = stmt.where(VinylRecord.is_trashed.is_(False))
    stmt = stmt.order_by(VinylRecord.created_at.asc(), VinylRecord.id.asc())
    return list(db.scalars(stmt))


def list_candidate_records(
    db: Session,
    *,
    display_date: date,
    exclude_ids: set[int] | None = None,
) -> list[VinylRecord]:
    stmt = (
        select(VinylRecord)
        .where(VinylRecord.is_trashed.is_(False))
        .where((VinylRecord.selected_for_date.is_(None)) | (VinylRecord.selected_for_date != display_date))
        .order_by(VinylRecord.created_at.asc(), VinylRecord.id.asc())
    )
    if exclude_ids:
        stmt = stmt.where(VinylRecord.id.not_in(sorted(exclude_ids)))
    return list(db.scalars(stmt))


def list_trashed_records(db: Session, *, limit: int = 24) -> list[VinylRecord]:
    stmt = (
        select(VinylRecord)
        .where(VinylRecord.is_trashed.is_(True))
        .order_by(VinylRecord.tossed_at.desc(), VinylRecord.id.desc())
        .limit(limit)
    )
    return list(db.scalars(stmt))


def count_records(db: Session) -> int:
    stmt = select(func.count(VinylRecord.id))
    return int(db.scalar(stmt) or 0)


def count_trashed_records(db: Session) -> int:
    stmt = select(func.count(VinylRecord.id)).where(VinylRecord.is_trashed.is_(True))
    return int(db.scalar(stmt) or 0)
