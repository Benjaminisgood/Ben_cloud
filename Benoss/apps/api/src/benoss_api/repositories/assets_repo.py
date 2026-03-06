from __future__ import annotations

from datetime import date

from sqlalchemy import or_
from sqlalchemy.orm import Session

from ..models import DailyDigestJob, GeneratedAsset


def _visible_filter(viewer_user_id: int):
    return or_(GeneratedAsset.visibility == "public", GeneratedAsset.user_id == viewer_user_id)


def list_ready_generated_assets(
    db: Session,
    *,
    viewer_user_id: int,
    kind: str,
    source_day: date | None,
    is_daily_digest: bool | None,
    before_id: int | None,
    limit: int,
) -> list[GeneratedAsset]:
    query = db.query(GeneratedAsset).filter(_visible_filter(viewer_user_id), GeneratedAsset.status == "ready")
    if kind:
        query = query.filter(GeneratedAsset.kind == kind)
    if source_day is not None:
        query = query.filter(GeneratedAsset.source_day == source_day)
    if is_daily_digest is not None:
        query = query.filter(GeneratedAsset.is_daily_digest == is_daily_digest)
    if before_id:
        query = query.filter(GeneratedAsset.id < before_id)
    return query.order_by(GeneratedAsset.id.desc()).limit(limit + 1).all()


def get_generated_asset(db: Session, *, asset_id: int) -> GeneratedAsset | None:
    return db.get(GeneratedAsset, asset_id)


def list_digest_jobs(db: Session, *, limit: int) -> list[DailyDigestJob]:
    return db.query(DailyDigestJob).order_by(DailyDigestJob.day.desc()).limit(limit).all()


def get_digest_job(db: Session, *, day: date, timezone: str) -> DailyDigestJob | None:
    return db.query(DailyDigestJob).filter_by(day=day, timezone=timezone).first()
