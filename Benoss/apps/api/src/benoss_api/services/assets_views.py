from __future__ import annotations

from datetime import datetime

from ..models import DailyDigestJob, GeneratedAsset
from ..utils.file_types import detect_file_type
from ..utils.oss import get_object_bytes


def asset_visible(asset: GeneratedAsset, *, viewer_user_id: int) -> bool:
    return asset.visibility == "public" or asset.user_id == viewer_user_id


def parse_source_day(source_day: str) -> datetime.date | None:
    if not source_day:
        return None
    try:
        return datetime.strptime(source_day, "%Y-%m-%d").date()
    except ValueError:
        return None


def parse_day(day: str) -> datetime.date:
    return datetime.strptime(day, "%Y-%m-%d").date()


def asset_payload(asset: GeneratedAsset) -> dict:
    file_type = asset.file_type or ("web" if asset.kind == "blog_html" else detect_file_type(asset.content_type, asset.ext))
    return {
        "id": asset.id,
        "kind": asset.kind,
        "title": asset.title or "",
        "provider": asset.provider or "",
        "model": asset.model or "",
        "visibility": asset.visibility,
        "status": asset.status,
        "is_daily_digest": bool(asset.is_daily_digest),
        "source_day": str(asset.source_day) if asset.source_day else None,
        "file_type": file_type,
        "content_type": asset.content_type or "",
        "size_bytes": int(asset.size_bytes or 0),
        "oss_key": asset.oss_key or "",
        "created_at": asset.created_at.isoformat() + "Z" if asset.created_at else None,
        "blob_url": f"/api/generated-assets/{asset.id}/blob",
    }


def job_payload(job: DailyDigestJob) -> dict:
    return {
        "day": str(job.day),
        "timezone": job.timezone,
        "status": job.status,
        "started_at": job.started_at.isoformat() + "Z" if job.started_at else None,
        "finished_at": job.finished_at.isoformat() + "Z" if job.finished_at else None,
        "error": job.error or "",
        "blog_asset_id": job.blog_asset_id,
        "podcast_asset_id": job.podcast_asset_id,
        "poster_asset_id": job.poster_asset_id,
        "blog_asset": asset_payload(job.blog_asset) if job.blog_asset else None,
        "podcast_asset": asset_payload(job.podcast_asset) if job.podcast_asset else None,
        "poster_asset": asset_payload(job.poster_asset) if job.poster_asset else None,
    }


def list_assets_response(rows: list[GeneratedAsset], *, limit: int) -> dict:
    has_more = len(rows) > limit
    return {"items": [asset_payload(asset) for asset in rows[:limit]], "has_more": has_more}


def read_asset_blob(asset: GeneratedAsset) -> bytes:
    return get_object_bytes(asset.oss_key)
