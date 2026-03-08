
from __future__ import annotations

from collections.abc import Iterable
from datetime import date

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..models import Photo


def list_photos(db: Session, *, limit: int = 200) -> list[Photo]:
    stmt = select(Photo).order_by(Photo.created_at.desc()).limit(limit)
    return list(db.execute(stmt).scalars().all())


def get_photo_by_id(db: Session, photo_id: int) -> Photo | None:
    stmt = select(Photo).where(Photo.id == photo_id)
    return db.execute(stmt).scalar_one_or_none()


def get_photo_by_oss_path(db: Session, oss_path: str) -> Photo | None:
    stmt = select(Photo).where(Photo.oss_path == oss_path)
    return db.execute(stmt).scalar_one_or_none()


def list_selected_photos(
    db: Session,
    *,
    display_date: date,
    include_trashed: bool,
) -> list[Photo]:
    stmt = select(Photo).where(Photo.selected_for_date == display_date)
    if not include_trashed:
        stmt = stmt.where(Photo.is_trashed.is_(False))
    stmt = stmt.order_by(Photo.created_at.asc(), Photo.id.asc())
    return list(db.execute(stmt).scalars().all())


def list_candidate_photos(
    db: Session,
    *,
    exclude_ids: Iterable[int] = (),
) -> list[Photo]:
    stmt = select(Photo).where(Photo.is_trashed.is_(False))
    exclude_ids = tuple(exclude_ids)
    if exclude_ids:
        stmt = stmt.where(Photo.id.notin_(exclude_ids))
    stmt = stmt.order_by(Photo.created_at.asc(), Photo.id.asc())
    return list(db.execute(stmt).scalars().all())


def list_trashed_photos(db: Session, *, limit: int = 24) -> list[Photo]:
    stmt = (
        select(Photo)
        .where(Photo.is_trashed.is_(True))
        .order_by(Photo.tossed_at.desc(), Photo.updated_at.desc(), Photo.id.desc())
        .limit(limit)
    )
    return list(db.execute(stmt).scalars().all())


def count_photos(db: Session) -> int:
    return int(db.execute(select(func.count(Photo.id))).scalar_one())


def count_trashed_photos(db: Session) -> int:
    stmt = select(func.count(Photo.id)).where(Photo.is_trashed.is_(True))
    return int(db.execute(stmt).scalar_one())
