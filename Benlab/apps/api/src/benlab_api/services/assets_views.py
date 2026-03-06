from __future__ import annotations

import mimetypes
from datetime import datetime
from pathlib import Path

from benlab_api.models import Attachment
from benlab_api.services.uploads import abs_attachment_path


def _iso_datetime(dt: datetime | None) -> str | None:
    return dt.isoformat() + "Z" if dt else None


def _detect_file_type(filename: str) -> str:
    ext = Path(filename or "").suffix.lower()
    guessed = mimetypes.guess_type(filename or "")[0] or ""

    if guessed.startswith("image/"):
        return "image"
    if guessed.startswith("video/"):
        return "video"
    if guessed.startswith("audio/"):
        return "audio"
    if guessed.startswith("text/"):
        return "text"

    if ext in {".html", ".htm"}:
        return "web"
    if ext in {".log"}:
        return "log"
    if ext in {".db", ".sqlite", ".sqlite3"}:
        return "database"
    if ext in {".zip", ".tar", ".gz", ".bz2", ".xz", ".rar", ".7z"}:
        return "archive"
    if ext in {".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx", ".md"}:
        return "document"
    return "file"


def parse_source_day(source_day: str) -> datetime.date | None:
    if not source_day:
        return None
    try:
        return datetime.strptime(source_day, "%Y-%m-%d").date()
    except ValueError:
        return None


def parse_day(day: str) -> datetime.date:
    return datetime.strptime(day, "%Y-%m-%d").date()


def _size_bytes(asset: Attachment) -> int:
    path = abs_attachment_path(asset.filename)
    if not path.exists() or not path.is_file():
        return 0
    return int(path.stat().st_size)


def _is_daily_digest(asset: Attachment) -> bool:
    return "digest" in (asset.filename or "").lower()


def asset_payload(asset: Attachment) -> dict:
    file_type = _detect_file_type(asset.filename)
    return {
        "id": asset.id,
        "kind": "attachment",
        "title": asset.filename or "",
        "provider": "",
        "model": "",
        "visibility": "private",
        "status": "ready",
        "is_daily_digest": _is_daily_digest(asset),
        "source_day": str(asset.created_at.date()) if asset.created_at else None,
        "file_type": file_type,
        "content_type": mimetypes.guess_type(asset.filename or "")[0] or "application/octet-stream",
        "size_bytes": _size_bytes(asset),
        "oss_key": "",
        "created_at": _iso_datetime(asset.created_at),
        "blob_url": f"/api/generated-assets/{asset.id}/blob",
    }


def job_payload(job: dict, *, blog_asset: Attachment | None, podcast_asset: Attachment | None, poster_asset: Attachment | None) -> dict:
    return {
        "day": str(job.get("day") or ""),
        "timezone": str(job.get("timezone") or "Asia/Shanghai"),
        "status": str(job.get("status") or "queued"),
        "started_at": job.get("started_at"),
        "finished_at": job.get("finished_at"),
        "error": str(job.get("error") or ""),
        "blog_asset_id": job.get("blog_asset_id"),
        "podcast_asset_id": job.get("podcast_asset_id"),
        "poster_asset_id": job.get("poster_asset_id"),
        "blog_asset": asset_payload(blog_asset) if blog_asset else None,
        "podcast_asset": asset_payload(podcast_asset) if podcast_asset else None,
        "poster_asset": asset_payload(poster_asset) if poster_asset else None,
    }


def asset_visible(asset: Attachment, *, viewer_user_id: int) -> bool:  # noqa: ARG001 - keep same API
    return True


def list_assets_response(rows: list[Attachment], *, limit: int) -> dict:
    has_more = len(rows) > limit
    return {"items": [asset_payload(asset) for asset in rows[:limit]], "has_more": has_more}


def read_asset_blob(asset: Attachment) -> bytes:
    path = abs_attachment_path(asset.filename)
    if not path.exists() or not path.is_file():
        raise FileNotFoundError(asset.filename)
    return path.read_bytes()
