"""Digest job read endpoints."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ...db.session import get_db
from ...models import Member
from ...repositories.assets_api_repo import get_generated_asset
from ...repositories.digest_api_repo import get_digest_job, list_digest_jobs
from ...services.assets_views import job_payload, parse_day
from ..deps import require_api_user

router = APIRouter(tags=["assets"])


@router.get("/digest/jobs")
def list_digest_jobs_endpoint(
    limit: int = Query(10, ge=1, le=50),
    user: Member = Depends(require_api_user),
    db: Session = Depends(get_db),
):
    rows = list_digest_jobs(db, limit=limit)
    items = []
    for row in rows:
        blog_asset = get_generated_asset(db, asset_id=row.get("blog_asset_id")) if row.get("blog_asset_id") else None
        podcast_asset = get_generated_asset(db, asset_id=row.get("podcast_asset_id")) if row.get("podcast_asset_id") else None
        poster_asset = get_generated_asset(db, asset_id=row.get("poster_asset_id")) if row.get("poster_asset_id") else None
        items.append(
            job_payload(
                row,
                blog_asset=blog_asset,
                podcast_asset=podcast_asset,
                poster_asset=poster_asset,
            )
        )
    return {"items": items}


@router.get("/digest/jobs/{day}")
def get_digest_job_endpoint(
    day: str,
    timezone: str = Query("Asia/Shanghai"),
    user: Member = Depends(require_api_user),
    db: Session = Depends(get_db),
):
    try:
        day_date = parse_day(day)
    except ValueError:
        raise HTTPException(status_code=400, detail="invalid day format")

    job = get_digest_job(db, day=day_date, timezone=timezone)
    if not job:
        raise HTTPException(status_code=404, detail="not found")

    blog_asset = get_generated_asset(db, asset_id=job.get("blog_asset_id")) if job.get("blog_asset_id") else None
    podcast_asset = get_generated_asset(db, asset_id=job.get("podcast_asset_id")) if job.get("podcast_asset_id") else None
    poster_asset = get_generated_asset(db, asset_id=job.get("poster_asset_id")) if job.get("poster_asset_id") else None
    return job_payload(
        job,
        blog_asset=blog_asset,
        podcast_asset=podcast_asset,
        poster_asset=poster_asset,
    )
