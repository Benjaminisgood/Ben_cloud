"""Digest job read endpoints."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ...db.session import get_db
from ...models import User
from ...repositories.assets_repo import get_digest_job, list_digest_jobs
from ...services.assets_views import job_payload, parse_day
from ..deps import require_api_user

router = APIRouter(tags=["assets"])


@router.get("/digest/jobs")
def list_digest_jobs_endpoint(
    limit: int = Query(10, ge=1, le=50),
    user: User = Depends(require_api_user),
    db: Session = Depends(get_db),
):
    rows = list_digest_jobs(db, limit=limit)
    return {"items": [job_payload(job) for job in rows]}


@router.get("/digest/jobs/{day}")
def get_digest_job_endpoint(
    day: str,
    timezone: str = Query("Asia/Shanghai"),
    user: User = Depends(require_api_user),
    db: Session = Depends(get_db),
):
    try:
        day_date = parse_day(day)
    except ValueError:
        raise HTTPException(status_code=400, detail="invalid day format")

    job = get_digest_job(db, day=day_date, timezone=timezone)
    if not job:
        raise HTTPException(status_code=404, detail="not found")
    return job_payload(job)
