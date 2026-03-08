from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from benreel_api.core.config import get_settings
from benreel_api.db.session import get_db
from benreel_api.services.programming import build_dashboard_snapshot

from ..deps import get_session_user
from ..templating import render_template

router = APIRouter(tags=["pages"])


@router.get("/", response_class=HTMLResponse)
def dashboard(request: Request, db: Session = Depends(get_db)):
    settings = get_settings()
    viewer = get_session_user(request)
    snapshot = build_dashboard_snapshot(
        db,
        manifest_path=settings.VIDEO_LIBRARY_PATH,
        daily_video_count=settings.DAILY_VIDEO_COUNT,
        viewer=viewer,
    )
    return render_template(
        request,
        "dashboard.html",
        {
            "title": "Benreel",
            "snapshot": snapshot,
            "theme": {
                "primary": "#6d2d12",
                "secondary": "#d4813c",
                "canvas": "#ead7b2",
                "ink": "#23140f",
            },
        },
    )


@router.get("/portal")
def portal() -> RedirectResponse:
    return RedirectResponse("/", status_code=303)
