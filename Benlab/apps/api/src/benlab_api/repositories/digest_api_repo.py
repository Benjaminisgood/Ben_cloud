from __future__ import annotations

import json
from datetime import UTC, date, datetime, time, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from benlab_api.models import Attachment, Log

_DIGEST_ACTION_TYPE = "digest_daily"


def _day_bounds(value: date) -> tuple[datetime, datetime]:
    start = datetime.combine(value, time.min)
    return start, start + timedelta(days=1)


def _iso_datetime(dt: datetime | None) -> str | None:
    return dt.isoformat() + "Z" if dt else None


def _parse_details(details: str) -> dict:
    if not details:
        return {}
    try:
        payload = json.loads(details)
    except (TypeError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _safe_int(value) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _job_from_log(log: Log) -> dict:
    payload = _parse_details(log.details)

    raw_asset_ids = payload.get("asset_ids") or []
    if not isinstance(raw_asset_ids, list):
        raw_asset_ids = []
    asset_ids = [asset_id for asset_id in (_safe_int(v) for v in raw_asset_ids) if asset_id is not None]

    return {
        "day": str(payload.get("day") or ""),
        "timezone": str(payload.get("timezone") or "Asia/Shanghai"),
        "status": str(payload.get("status") or "queued"),
        "started_at": str(payload.get("started_at") or _iso_datetime(log.timestamp)),
        "finished_at": str(payload.get("finished_at") or "") or None,
        "error": str(payload.get("error") or ""),
        "blog_asset_id": asset_ids[0] if len(asset_ids) > 0 else None,
        "podcast_asset_id": asset_ids[1] if len(asset_ids) > 1 else None,
        "poster_asset_id": asset_ids[2] if len(asset_ids) > 2 else None,
    }


def list_daily_assets(db: Session, *, day: date) -> list[Attachment]:
    start, end = _day_bounds(day)
    stmt = select(Attachment).where(Attachment.created_at >= start, Attachment.created_at < end).order_by(Attachment.id.desc())
    return db.scalars(stmt).all()


def list_digest_jobs(db: Session, *, limit: int) -> list[dict]:
    logs = db.scalars(
        select(Log)
        .where(Log.action_type == _DIGEST_ACTION_TYPE)
        .order_by(Log.timestamp.desc(), Log.id.desc())
        .limit(limit)
    ).all()
    return [_job_from_log(log) for log in logs]


def get_digest_job(db: Session, *, day: date, timezone: str) -> dict | None:
    day_text = day.isoformat()
    logs = db.scalars(
        select(Log)
        .where(Log.action_type == _DIGEST_ACTION_TYPE)
        .order_by(Log.timestamp.desc(), Log.id.desc())
    ).all()
    for log in logs:
        job = _job_from_log(log)
        if job["day"] == day_text and job["timezone"] == timezone:
            return job
    return None


def save_digest_job(
    db: Session,
    *,
    user_id: int,
    day: date,
    timezone: str,
    status: str,
    force: bool,
    asset_ids: list[int],
    error: str,
) -> dict:
    now_text = _iso_datetime(datetime.now(UTC).replace(tzinfo=None))
    details = {
        "day": day.isoformat(),
        "timezone": timezone,
        "status": status,
        "force": force,
        "asset_ids": asset_ids,
        "error": error,
        "started_at": now_text,
        "finished_at": now_text if status == "ready" else None,
    }
    row = Log(
        user_id=user_id,
        action_type=_DIGEST_ACTION_TYPE,
        details=json.dumps(details, ensure_ascii=False),
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return _job_from_log(row)
