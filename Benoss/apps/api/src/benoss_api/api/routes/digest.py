"""Digest build endpoints for web-only deployment."""

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from ...db.session import get_db
from ...repositories.digest_repo import get_or_create_digest_job, list_ready_daily_assets
from ...services.digest_views import (
    digest_refresh_response,
    parse_digest_request,
    refresh_job_from_assets,
    resolve_digest_day,
)
from ...utils.runtime_settings import get_setting_str
from ...models import User
from ..deps import require_api_admin

router = APIRouter(tags=["digest"])


@router.post("/digest/daily")
async def trigger_daily_digest(
    request: Request,
    user: User = Depends(require_api_admin),
    db: Session = Depends(get_db),
):
    """Refresh digest job metadata from existing generated assets."""
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

    assets = list_ready_daily_assets(db, day=day_value)
    job = get_or_create_digest_job(db, day=day_value, timezone=timezone_name)
    refresh_job_from_assets(job, assets)
    db.commit()

    return digest_refresh_response(
        day_value=day_value,
        timezone_name=timezone_name,
        force=force,
        assets=assets,
        error=job.error or "",
    )
