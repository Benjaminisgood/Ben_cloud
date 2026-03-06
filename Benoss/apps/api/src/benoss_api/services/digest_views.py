from __future__ import annotations

from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

from ..models import DailyDigestJob, GeneratedAsset


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
        tz = __import__("datetime").timezone.utc
    return datetime.now(tz).date() - timedelta(days=1)


def refresh_job_from_assets(job: DailyDigestJob, assets: list[GeneratedAsset]) -> None:
    if assets:
        job.status = "ready"
        job.error = ""
        job.finished_at = datetime.now(UTC).replace(tzinfo=None)
    else:
        job.status = "queued"
        job.error = (
            "No digest assets found for this day. "
            "In web-only mode, digest assets must be produced by the current AI pipeline first."
        )
        job.finished_at = None

    kind_to_asset_id = {asset.kind: asset.id for asset in assets}
    job.blog_asset_id = kind_to_asset_id.get("blog_html")
    job.podcast_asset_id = kind_to_asset_id.get("podcast_audio")
    job.poster_asset_id = kind_to_asset_id.get("poster_image")


def digest_refresh_response(*, day_value, timezone_name: str, force: bool, assets: list[GeneratedAsset], error: str) -> dict:
    return {
        "day": day_value.isoformat(),
        "timezone": timezone_name,
        "status": "ready" if assets else "queued",
        "force": force,
        "assets": [
            {
                "id": asset.id,
                "kind": asset.kind,
                "title": asset.title or "",
                "blob_url": f"/api/generated-assets/{asset.id}/blob",
            }
            for asset in assets
        ],
        "message": "Digest metadata refreshed from generated assets.",
        "error": error,
    }
