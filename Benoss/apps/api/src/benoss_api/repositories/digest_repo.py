from __future__ import annotations

from datetime import date

from sqlalchemy.orm import Session

from ..models import DailyDigestJob, GeneratedAsset


def list_ready_daily_assets(db: Session, *, day: date) -> list[GeneratedAsset]:
    return (
        db.query(GeneratedAsset)
        .filter(
            GeneratedAsset.source_day == day,
            GeneratedAsset.is_daily_digest.is_(True),
            GeneratedAsset.status == "ready",
        )
        .order_by(GeneratedAsset.id.desc())
        .all()
    )


def get_digest_job(db: Session, *, day: date, timezone: str) -> DailyDigestJob | None:
    return db.query(DailyDigestJob).filter_by(day=day, timezone=timezone).first()


def get_or_create_digest_job(db: Session, *, day: date, timezone: str) -> DailyDigestJob:
    job = get_digest_job(db, day=day, timezone=timezone)
    if job is None:
        job = DailyDigestJob(day=day, timezone=timezone)
        db.add(job)
    return job
