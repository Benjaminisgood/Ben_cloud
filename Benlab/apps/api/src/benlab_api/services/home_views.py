from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from benlab_api.models import Attachment, Message
from benlab_api.services.records_service import extract_tags_from_message, preview_text


def resolve_timezone() -> tuple[object, str]:
    tz_name = (os.getenv("DIGEST_TIMEZONE", "Asia/Shanghai") or "Asia/Shanghai").strip()
    try:
        return ZoneInfo(tz_name), tz_name
    except Exception:
        return timezone.utc, "UTC"


def get_today_context() -> tuple[object, object, str]:
    tz, tz_name = resolve_timezone()
    today = datetime.now(tz).date()
    yesterday = today - timedelta(days=1)
    return today, yesterday, tz_name


def public_record_payload(record: Message) -> dict:
    return {
        "id": record.id,
        "record_no": record.id,
        "preview": preview_text(record.content or ""),
        "tags": extract_tags_from_message(record),
        "created_at": record.timestamp.isoformat() + "Z" if record.timestamp else None,
        "user": {
            "id": record.sender.id if record.sender else record.sender_id,
            "username": record.sender.username if record.sender else "",
        },
    }


def digest_asset_payload(asset: Attachment) -> dict:
    return {
        "id": asset.id,
        "kind": "attachment",
        "title": asset.filename or "",
        "source_day": asset.created_at.date().isoformat() if asset.created_at else None,
        "created_at": asset.created_at.isoformat() + "Z" if asset.created_at else None,
        "blob_url": f"/api/contents/{asset.id}/blob",
    }


def build_home_today_response(
    *,
    today,
    yesterday,
    timezone_name: str,
    public_records: list[Message],
    digest_assets: list[Attachment],
    public_count: int,
    user_count: int,
    top_tags_rows,
) -> dict:
    return {
        "date": today.isoformat(),
        "timezone": timezone_name,
        "digest_day": yesterday.isoformat(),
        "public_records": [public_record_payload(record) for record in public_records],
        "digest_assets": [digest_asset_payload(asset) for asset in digest_assets],
        "ai": {"message": "已启用"},
        "archive": {
            "saved": True,
            "archive": {
                "day": yesterday.isoformat(),
                "record_count": len(public_records),
                "changed": False,
            },
        },
        "metrics": {
            "public_count": public_count,
            "user_count": user_count,
            "top_tags": [name for name, _count in top_tags_rows],
        },
    }
