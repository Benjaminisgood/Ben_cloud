from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from benvinyl_api.db.session import get_db
from benvinyl_api.schemas.record import VinylRecordCreate, VinylRecordUpdate
from benvinyl_api.services.records import DuplicateVinylRecordError, VinylRecordNotFoundError, create_record, update_record
from benvinyl_api.services.vinyl_room import build_dashboard_snapshot

from ..deps import get_session_user
from ..templating import render_template

router = APIRouter(tags=["pages"])

_FLASH_MESSAGES = {
    "duplicate": "这张唱片已经登记过了。",
    "missing": "请至少填写一个 OSS URL 或对象 key。",
    "missing-record": "没有找到这张唱片。",
    "restored": "唱片已经从垃圾桶捡回并放回节目堆。",
    "saved": "新唱片已经放进唱片池。",
    "trashed": "唱片已经丢进垃圾桶。",
}


def _is_admin(user: dict[str, str] | None) -> bool:
    return bool(user and user.get("role") == "admin")


@router.get("/", response_class=HTMLResponse)
def dashboard(
    request: Request,
    record_id: int | None = Query(default=None),
    flash: str | None = Query(default=None),
    db: Session = Depends(get_db),
):
    current_user = get_session_user(request)
    snapshot = build_dashboard_snapshot(db, active_record_id=record_id).model_dump()
    return render_template(
        request,
        "dashboard.html",
        {
            "title": "Benvinyl",
            "nav_label": "Vinyl Room",
            "hero_title": "黑胶唱片机",
            "hero_subtitle": "把 OSS 音频排成每天固定开播的一小叠唱片，像桌面上的私人节目单。",
            "hero_tags": ["每日节目", "黑胶唱盘", "垃圾桶回收"],
            "story_label": "站点作用",
            "story_title": "让每天的音频展示像一张有限定曲目的黑胶桌面",
            "story_body": "这个站只记录你的 OSS 音频引用，不做分类和复杂运营，只负责把当天节目稳定摆上桌。",
            "trash_label": "垃圾桶规则",
            "trash_title": "不喜欢就先扔，想恢复再捡回",
            "trash_hint": "下架不会删掉唱片引用，只会把它移出公开节目；恢复时会重新塞回今天的唱片堆。",
            "focus_title": "管理员动作",
            "focus_intro": "管理员登录后可以录入新唱片、拖拽到垃圾桶，或从垃圾桶恢复。",
            "current_user": current_user or {"username": "public", "role": "public"},
            "is_admin": _is_admin(current_user),
            "dashboard": snapshot,
            "flash_message": _FLASH_MESSAGES.get(flash or "", ""),
            "theme": {
                "primary": "#5b3424",
                "secondary": "#c69c54",
                "canvas": "#efe2ca",
                "ink": "#19120d",
            },
        },
    )


@router.get("/portal")
def portal() -> RedirectResponse:
    return RedirectResponse("/", status_code=303)


@router.post("/records")
async def create_record_page(request: Request, db: Session = Depends(get_db)):
    current_user = get_session_user(request)
    if not _is_admin(current_user):
        return RedirectResponse("/login", status_code=303)

    form = await request.form()
    title = str(form.get("title", "")).strip()
    note = str(form.get("note", "")).strip()
    oss_path = str(form.get("oss_path", "")).strip()
    if not oss_path:
        return RedirectResponse("/?flash=missing", status_code=303)

    try:
        record = create_record(
            db,
            payload=VinylRecordCreate(title=title, note=note, oss_path=oss_path),
            added_by=current_user["username"],
        )
    except DuplicateVinylRecordError:
        return RedirectResponse("/?flash=duplicate", status_code=303)

    return RedirectResponse(f"/?record_id={record.id}&flash=saved", status_code=303)


@router.post("/records/{record_id}/trash")
def trash_record_page(record_id: int, request: Request, db: Session = Depends(get_db)):
    current_user = get_session_user(request)
    if not _is_admin(current_user):
        return RedirectResponse("/login", status_code=303)
    try:
        update_record(db, record_id=record_id, payload=VinylRecordUpdate(is_trashed=True))
    except VinylRecordNotFoundError:
        return RedirectResponse("/?flash=missing-record", status_code=303)
    return RedirectResponse("/?flash=trashed", status_code=303)


@router.post("/records/{record_id}/restore")
def restore_record_page(record_id: int, request: Request, db: Session = Depends(get_db)):
    current_user = get_session_user(request)
    if not _is_admin(current_user):
        return RedirectResponse("/login", status_code=303)
    try:
        update_record(db, record_id=record_id, payload=VinylRecordUpdate(is_trashed=False))
    except VinylRecordNotFoundError:
        return RedirectResponse("/?flash=missing-record", status_code=303)
    return RedirectResponse(f"/?record_id={record_id}&flash=restored", status_code=303)
