
from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from pydantic import ValidationError
from sqlalchemy.orm import Session

from benhealth_api.core.config import get_settings
from benhealth_api.db.session import get_db
from benhealth_api.schemas.health_record import HealthRecordCreate
from benhealth_api.services.health_records import create_health_record, list_health_records
from benhealth_api.services.legacy_data import get_dashboard_snapshot

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
    health_records = list_health_records(
        db,
        viewer_username=user["username"],
        viewer_is_admin=user["role"] == "admin",
        limit=12,
    )
    return render_template(
        request,
        "dashboard.html",
        {
            "title": "Benhealth",
            "nav_label": "Health",
            "hero_title": "🫀 健康仪表站",
            "hero_subtitle": "把运动、身体指标与营养记录整理成清晰的自我照护界面。",
            "collections_title": "健康切片",
            "collections_subtitle": "运动、身体指标与饮食汇总",
            "records_label": "健康记录",
            "records_hint": "让 agent 针对习惯、饮食、心理、运动、医疗持续写入健康记录，管理员再做修正和归档。",
            "dashboard": dashboard,
            "health_records": health_records,
            "current_user": user,
            "theme": {
                "primary": "#0f6d62",
                "secondary": "#56c596",
                "canvas": "#e9f5ef",
                "ink": "#173630",
            },
        },
    )


@router.get("/portal")
def portal() -> RedirectResponse:
    return RedirectResponse("/", status_code=303)


@router.post("/health-records")
async def submit_health_record(request: Request, db: Session = Depends(get_db)):
    user = get_session_user(request)
    if not user:
        return RedirectResponse("/login", status_code=303)
    form = await request.form()
    title = str(form.get("title", "")).strip()
    summary = str(form.get("summary", "")).strip()
    if not title or not summary:
        return RedirectResponse("/", status_code=303)
    metric_value_raw = str(form.get("metric_value", "")).strip()
    try:
        payload = HealthRecordCreate(
            domain=str(form.get("domain", "habit")),
            title=title,
            summary=summary,
            care_status=str(form.get("care_status", "active")),
            concern_level=str(form.get("concern_level", "medium")),
            frequency=str(form.get("frequency", "once")),
            next_review_on=str(form.get("next_review_on", "")).strip() or None,
            metric_name=str(form.get("metric_name", "")).strip() or None,
            metric_value=float(metric_value_raw) if metric_value_raw else None,
            metric_unit=str(form.get("metric_unit", "")).strip() or None,
            food_name=str(form.get("food_name", "")).strip() or None,
            exercise_name=str(form.get("exercise_name", "")).strip() or None,
            provider_name=str(form.get("provider_name", "")).strip() or None,
            medication_name=str(form.get("medication_name", "")).strip() or None,
            follow_up_plan=str(form.get("follow_up_plan", "")).strip() or None,
            agent_note=str(form.get("agent_note", "")).strip() or None,
        )
    except (ValidationError, ValueError):
        return RedirectResponse("/", status_code=303)
    create_health_record(db, payload=payload, actor=user["username"], actor_role=user["role"])
    return RedirectResponse("/", status_code=303)
