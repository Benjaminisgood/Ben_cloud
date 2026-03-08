from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session

from benreel_api.db.session import get_db
from benreel_api.repositories.video_items_repo import get_video_item, list_video_items
from benreel_api.schemas.video_item import VideoItemRead, VideoItemStatus, VideoItemStatusUpdate
from benreel_api.services.programming import sync_video_sources, update_video_status
from benreel_api.core.config import get_settings

from ..deps import get_session_user, require_admin

router = APIRouter(tags=["videos"])


@router.get("/videos", response_model=list[VideoItemRead])
def get_videos(
    request: Request,
    status: VideoItemStatus = Query(default="active"),
    db: Session = Depends(get_db),
) -> list[VideoItemRead]:
    sync_video_sources(db, get_settings().VIDEO_LIBRARY_PATH)
    viewer = get_session_user(request)
    if status == "trashed" and (not viewer or viewer["role"] != "admin"):
        raise HTTPException(status_code=403, detail="admin_required")
    return list_video_items(db, status=status)


@router.patch("/videos/{video_id}", response_model=VideoItemRead)
def patch_video(
    video_id: int,
    payload: VideoItemStatusUpdate,
    user: dict[str, str] = Depends(require_admin),
    db: Session = Depends(get_db),
) -> VideoItemRead:
    if not get_video_item(db, video_id):
        raise HTTPException(status_code=404, detail="video_not_found")
    return update_video_status(db, video_id=video_id, status=payload.status, actor=user["username"])
