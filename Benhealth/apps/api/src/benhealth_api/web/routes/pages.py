
from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from pydantic import ValidationError
from sqlalchemy.orm import Session

from benhealth_api.core.config import get_settings
from benhealth_api.db.session import get_db
from benhealth_api.schemas.health_record import HealthRecordCreate, HealthRecordReview
from benhealth_api.services.health_records import (
    create_health_record,
    list_health_records,
    reject_health_record,
    review_health_record,
)
from benhealth_api.services.legacy_data import get_dashboard_snapshot

from ..deps import get_session_user
from ..templating import render_template

router = APIRouter(tags=["pages"])


def _arrange_health_records(records: list) -> list:
    pending = [item for item in records if item.review_status == "pending_review"]
    approved = [item for item in records if item.review_status == "approved"]
    rejected = [item for item in records if item.review_status not in {"pending_review", "approved"}]
    return [*pending, *approved, *rejected]


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
    health_records = _arrange_health_records(health_records)
    approved_count = sum(1 for item in health_records if item.review_status == "approved")
    pending_count = sum(1 for item in health_records if item.review_status == "pending_review")
    return render_template(
        request,
        "dashboard.html",
        {
            "title": "Benhealth",
            "nav_label": "Health",
            "hero_title": "身体监测台",
            "hero_subtitle": "节律、恢复、风险，一屏可读。",
            "collections_title": "健康切片",
            "collections_subtitle": "运动、指标、饮食",
            "records_label": "健康记录",
            "records_hint": "健康审阅面板",
            "dashboard": dashboard,
            "health_records": health_records,
            "approved_health_count": approved_count,
            "pending_health_count": pending_count,
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


@router.post("/health-records/{record_id}/review")
async def submit_health_review(record_id: int, request: Request, db: Session = Depends(get_db)):
    user = get_session_user(request)
    if not user:
        return RedirectResponse("/login", status_code=303)
    if user["role"] != "admin":
        return RedirectResponse("/", status_code=303)
    form = await request.form()
    review_status = str(form.get("review_status", "")).strip()
    if review_status == "approved":
        payload = HealthRecordReview(review_status="approved")
        review_health_record(db, record_id=record_id, payload=payload, actor=user["username"])
    elif review_status == "rejected":
        reject_health_record(db, record_id=record_id, actor=user["username"])
    return RedirectResponse("/", status_code=303)
