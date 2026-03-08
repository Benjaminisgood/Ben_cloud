
from __future__ import annotations

from pydantic import ValidationError
from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from benphoto_api.db.session import get_db
from benphoto_api.schemas.photo import PhotoCreate, PhotoUpdate
from benphoto_api.services.photo_desk import build_dashboard_snapshot
from benphoto_api.services.photos import DuplicatePhotoError, PhotoNotFoundError, create_photo, update_photo

from ..deps import get_session_user
from ..templating import render_template

router = APIRouter(tags=["pages"])

_FLASH_MESSAGES = {
    "added": "新照片已经塞进照片池里了。",
    "duplicate": "这张照片已经存在，没再重复添加。",
    "invalid": "照片地址不能为空，请检查后重试。",
    "tossed": "这张相纸已经被扔进垃圾桶。",
    "restored": "这张相纸已经从垃圾桶里捡回桌面。",
    "missing": "那张照片不存在，可能已经被移除。",
}


@router.get("/", response_class=HTMLResponse)
def dashboard(
    request: Request,
    flash: str | None = Query(default=None),
    db: Session = Depends(get_db),
):
    user = get_session_user(request)
    if not user:
        return RedirectResponse("/login", status_code=303)

    dashboard_snapshot = build_dashboard_snapshot(db).model_dump()
    return render_template(
        request,
        "dashboard.html",
        {
            "title": "Benphoto",
            "dashboard": dashboard_snapshot,
            "current_user": user,
            "flash_message": _FLASH_MESSAGES.get(flash),
            "theme": {
                "primary": "#cc6a2f",
                "secondary": "#ffd166",
                "canvas": "#f8efe1",
                "ink": "#2d2119",
                "wood": "#9d6035",
                "cream": "#fffaf3",
                "accent": "#4fa8a0",
            },
        },
    )


@router.get("/portal")
def portal() -> RedirectResponse:
    return RedirectResponse("/", status_code=303)


@router.post("/photos")
async def submit_photo(request: Request, db: Session = Depends(get_db)):
    user = get_session_user(request)
    if not user:
        return RedirectResponse("/login", status_code=303)

    form = await request.form()
    try:
        payload = PhotoCreate(
            title=str(form.get("title", "")),
            caption=str(form.get("caption", "")),
            oss_path=str(form.get("oss_path", "")),
        )
        create_photo(db, payload=payload, added_by=user["username"])
    except ValidationError:
        return RedirectResponse("/?flash=invalid", status_code=303)
    except DuplicatePhotoError:
        return RedirectResponse("/?flash=duplicate", status_code=303)
    return RedirectResponse("/?flash=added", status_code=303)


@router.post("/photos/{photo_id}/trash")
def trash_photo_page(photo_id: int, request: Request, db: Session = Depends(get_db)):
    user = get_session_user(request)
    if not user:
        return RedirectResponse("/login", status_code=303)
    try:
        update_photo(db, photo_id=photo_id, payload=PhotoUpdate(is_trashed=True))
    except PhotoNotFoundError:
        return RedirectResponse("/?flash=missing", status_code=303)
    return RedirectResponse("/?flash=tossed", status_code=303)


@router.post("/photos/{photo_id}/restore")
def restore_photo_page(photo_id: int, request: Request, db: Session = Depends(get_db)):
    user = get_session_user(request)
    if not user:
        return RedirectResponse("/login", status_code=303)
    try:
        update_photo(db, photo_id=photo_id, payload=PhotoUpdate(is_trashed=False))
    except PhotoNotFoundError:
        return RedirectResponse("/?flash=missing", status_code=303)
    return RedirectResponse("/?flash=restored", status_code=303)
