
from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from pydantic import ValidationError
from sqlalchemy.orm import Session

from benprefs_api.core.config import get_settings
from benprefs_api.db.session import get_db
from benprefs_api.schemas.preference_record import PreferenceRecordCreate
from benprefs_api.services.preference_records import create_preference_record, list_preference_records
from benprefs_api.services.legacy_data import get_dashboard_snapshot

from ..deps import get_session_user
from ..templating import render_template

router = APIRouter(tags=["pages"])


@router.get("/", response_class=HTMLResponse)
def dashboard(request: Request, db: Session = Depends(get_db)):
    user = get_session_user(request)
    if not user:
        return RedirectResponse("/login", status_code=303)
    settings = get_settings()
    dashboard = get_dashboard_snapshot(settings.SOURCE_DATABASE_PATH).model_dump()
    preference_records = list_preference_records(
        db,
        viewer_username=user["username"],
        viewer_is_admin=user["role"] == "admin",
        limit=12,
    )
    return render_template(
        request,
        "dashboard.html",
        {
            "title": "Benprefs",
            "nav_label": "Preferences",
            "hero_title": "💛 偏好档案站",
            "hero_subtitle": "把你在意的事物、偏好强度和网站习惯汇总成可浏览的长期画像。",
            "collections_title": "偏好切片",
            "collections_subtitle": "当前偏好、网站偏好与时间线变化",
            "records_label": "偏好记录",
            "records_hint": "让 agent 持续写入你对食物、商家、物品、行为和环境的喜恶判断，并按过去/当下/未来管理。",
            "dashboard": dashboard,
            "preference_records": preference_records,
            "current_user": user,
            "theme": {
                "primary": "#9b3d23",
                "secondary": "#f2a541",
                "canvas": "#f6eee3",
                "ink": "#2f2118",
            },
        },
    )


@router.get("/portal")
def portal() -> RedirectResponse:
    return RedirectResponse("/", status_code=303)


@router.post("/preference-records")
async def submit_preference_record(request: Request, db: Session = Depends(get_db)):
    user = get_session_user(request)
    if not user:
        return RedirectResponse("/login", status_code=303)
    form = await request.form()
    subject_name = str(form.get("subject_name", "")).strip()
    aspect = str(form.get("aspect", "")).strip()
    if not subject_name or not aspect:
        return RedirectResponse("/", status_code=303)
    try:
        payload = PreferenceRecordCreate(
            subject_type=str(form.get("subject_type", "other")),
            subject_name=subject_name,
            aspect=aspect,
            stance=str(form.get("stance", "neutral")),
            timeframe=str(form.get("timeframe", "current")),
            validation_state=str(form.get("validation_state", "hypothesis")),
            intensity=int(str(form.get("intensity", "5"))),
            certainty=int(str(form.get("certainty", "5"))),
            context=str(form.get("context", "")).strip() or None,
            merchant_name=str(form.get("merchant_name", "")).strip() or None,
            source_kind=str(form.get("source_kind", "manual")),
            trigger_detail=str(form.get("trigger_detail", "")).strip() or None,
            supporting_detail=str(form.get("supporting_detail", "")).strip() or None,
        )
    except (ValidationError, ValueError):
        return RedirectResponse("/", status_code=303)
    create_preference_record(db, payload=payload, actor=user["username"], actor_role=user["role"])
    return RedirectResponse("/", status_code=303)
