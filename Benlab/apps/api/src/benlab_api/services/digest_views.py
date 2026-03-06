from __future__ import annotations

from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from benlab_api.models import Attachment


def parse_digest_request(body: dict, *, default_timezone: str) -> tuple[str, str, bool]:
    timezone_name = str(body.get("timezone") or default_timezone).strip() or default_timezone
    day = str(body.get("day") or "").strip()
    force = bool(body.get("force"))
    return timezone_name, day, force


def resolve_digest_day(day_str: str, timezone_name: str):
    if day_str:
        return datetime.strptime(day_str, "%Y-%m-%d").date()

    try:
        tz = ZoneInfo(timezone_name)
    except Exception:
        tz = timezone.utc
    return datetime.now(tz).date() - timedelta(days=1)


def digest_refresh_response(*, day_value, timezone_name: str, force: bool, assets: list[Attachment], error: str) -> dict:
    return {
        "day": day_value.isoformat(),
        "timezone": timezone_name,
        "status": "ready" if assets else "queued",
        "force": force,
        "assets": [
            {
                "id": asset.id,
                "kind": "attachment",
                "title": asset.filename or "",
                "blob_url": f"/api/generated-assets/{asset.id}/blob",
            }
            for asset in assets
        ],
        "message": "Digest metadata refreshed from attachment snapshots.",
        "error": error,
    }
