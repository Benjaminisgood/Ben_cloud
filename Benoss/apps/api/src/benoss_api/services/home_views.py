from __future__ import annotations

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from ..models import GeneratedAsset, Record
from ..utils.runtime_settings import get_setting_str


def resolve_timezone() -> tuple[object, str]:
    tz_name = get_setting_str("DIGEST_TIMEZONE", default="Asia/Shanghai").strip() or "Asia/Shanghai"
    try:
        return ZoneInfo(tz_name), tz_name
    except Exception:
        from datetime import timezone

        return timezone.utc, "UTC"


def get_today_context() -> tuple[object, object, str]:
    tz, tz_name = resolve_timezone()
    today = datetime.now(tz).date()
    yesterday = today - timedelta(days=1)
    return today, yesterday, tz_name


def public_record_payload(record: Record) -> dict:
    return {
        "id": record.id,
        "record_no": record.id,
        "preview": record.preview or "",
        "tags": record.get_tags(),
        "created_at": record.created_at.isoformat() + "Z" if record.created_at else None,
        "user": {
            "id": record.user.id if record.user else record.user_id,
            "username": record.user.username if record.user else "",
        },
    }


def digest_asset_payload(asset: GeneratedAsset) -> dict:
    return {
        "id": asset.id,
        "kind": asset.kind,
        "title": asset.title or "",
        "source_day": asset.source_day.isoformat() if asset.source_day else None,
        "created_at": asset.created_at.isoformat() + "Z" if asset.created_at else None,
        "blob_url": f"/api/generated-assets/{asset.id}/blob",
    }


def build_home_today_response(
    *,
    today,
    yesterday,
    timezone_name: str,
    public_records: list[Record],
    digest_assets: list[GeneratedAsset],
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
