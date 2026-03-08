
from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from pydantic import ValidationError
from sqlalchemy.orm import Session

from benprefs_api.core.config import get_settings
from benprefs_api.db.session import get_db
from benprefs_api.schemas.preference_record import PreferenceRecordCreate, PreferenceRecordReview
from benprefs_api.services.preference_records import (
    create_preference_record,
    list_preference_records,
    reject_preference_record,
    review_preference_record,
)
from benprefs_api.services.legacy_data import get_dashboard_snapshot

from ..deps import get_session_user
from ..templating import render_template

router = APIRouter(tags=["pages"])


def _arrange_preference_records(records: list) -> list:
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
    preference_records = list_preference_records(
        db,
        viewer_username=user["username"],
        viewer_is_admin=user["role"] == "admin",
        limit=12,
    )
    preference_records = _arrange_preference_records(preference_records)
    approved_count = sum(1 for item in preference_records if item.review_status == "approved")
    pending_count = sum(1 for item in preference_records if item.review_status == "pending_review")
    return render_template(
        request,
        "dashboard.html",
        {
            "title": "Benprefs",
            "nav_label": "Preferences",
            "hero_title": "偏好档案局",
            "hero_subtitle": "喜欢、规避、想试，一眼看全。",
            "collections_title": "偏好切片",
            "collections_subtitle": "当前喜恶与网站习惯",
            "records_label": "偏好记录",
            "records_hint": "偏好审阅栈",
            "dashboard": dashboard,
            "preference_records": preference_records,
            "approved_preference_count": approved_count,
            "pending_preference_count": pending_count,
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


@router.post("/preference-records/{record_id}/review")
async def submit_preference_review(record_id: int, request: Request, db: Session = Depends(get_db)):
    user = get_session_user(request)
    if not user:
        return RedirectResponse("/login", status_code=303)
    if user["role"] != "admin":
        return RedirectResponse("/", status_code=303)
    form = await request.form()
    review_status = str(form.get("review_status", "")).strip()
    if review_status == "approved":
        payload = PreferenceRecordReview(review_status="approved")
        review_preference_record(db, record_id=record_id, payload=payload, actor=user["username"])
    elif review_status == "rejected":
        reject_preference_record(db, record_id=record_id, actor=user["username"])
    return RedirectResponse("/", status_code=303)
