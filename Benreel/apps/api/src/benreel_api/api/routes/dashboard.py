from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from benreel_api.core.config import get_settings
from benreel_api.db.session import get_db
from benreel_api.schemas.dashboard import DashboardSnapshot
from benreel_api.services.programming import build_dashboard_snapshot

from ..deps import get_session_user

router = APIRouter(tags=["dashboard"])


@router.get("/dashboard", response_model=DashboardSnapshot)
def dashboard(request: Request, db: Session = Depends(get_db)) -> DashboardSnapshot:
    settings = get_settings()
    viewer = get_session_user(request)
    return build_dashboard_snapshot(
        db,
        manifest_path=settings.VIDEO_LIBRARY_PATH,
        daily_video_count=settings.DAILY_VIDEO_COUNT,
        viewer=viewer,
    )
