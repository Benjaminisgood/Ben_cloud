"""Digest build endpoints for Benlab."""

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from ...db.session import get_db
from ...models import Member
from ...repositories.digest_api_repo import list_daily_assets, save_digest_job
from ...services.digest_views import digest_refresh_response, parse_digest_request, resolve_digest_day
from ...utils.runtime_settings import get_setting_str
from ..deps import require_api_admin

router = APIRouter(tags=["digest"])


@router.post("/digest/daily")
async def trigger_daily_digest(
    request: Request,
    user: Member = Depends(require_api_admin),
    db: Session = Depends(get_db),
):
    """Refresh digest metadata from attachment snapshots."""
    body = {}
    try:
        body = await request.json()
    except Exception:
        pass

    timezone_name, day_str, force = parse_digest_request(
        body,
        default_timezone=get_setting_str("DIGEST_TIMEZONE", default="Asia/Shanghai"),
    )

    try:
        day_value = resolve_digest_day(day_str, timezone_name)
    except ValueError:
        raise HTTPException(status_code=400, detail="invalid day format")

    assets = list_daily_assets(db, day=day_value)
    status = "ready" if assets else "queued"
    error = "" if assets else "No attachment snapshots found for this day."

    save_digest_job(
        db,
        user_id=user.id,
        day=day_value,
        timezone=timezone_name,
        status=status,
        force=force,
        asset_ids=[asset.id for asset in assets[:3]],
        error=error,
    )

    return digest_refresh_response(
        day_value=day_value,
        timezone_name=timezone_name,
        force=force,
        assets=assets,
        error=error,
    )
