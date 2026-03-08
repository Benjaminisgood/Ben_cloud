
from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from pydantic import ValidationError
from sqlalchemy.orm import Session

from benfinance_api.core.config import get_settings
from benfinance_api.db.session import get_db
from benfinance_api.schemas.finance_record import FinanceRecordCreate
from benfinance_api.services.finance_records import create_finance_record, list_finance_records
from benfinance_api.services.legacy_data import get_dashboard_snapshot

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
    finance_records = list_finance_records(
        db,
        viewer_username=user["username"],
        viewer_is_admin=user["role"] == "admin",
        limit=12,
    )
    return render_template(
        request,
        "dashboard.html",
        {
            "title": "Benfinance",
            "nav_label": "Finance",
            "hero_title": "💹 财务洞察站",
            "hero_subtitle": "把账户、交易、预算和储蓄目标收束成一套可持续追踪的资金看板。",
            "collections_title": "财务切片",
            "collections_subtitle": "账户、流水、预算与储蓄目标",
            "records_label": "财务记录",
            "records_hint": "让 agent 填收支、预算、账单、债务、订阅和财务决策，管理员再做修改、清理和归档。",
            "dashboard": dashboard,
            "finance_records": finance_records,
            "current_user": user,
            "theme": {
                "primary": "#183a5a",
                "secondary": "#d2a44c",
                "canvas": "#eef3f8",
                "ink": "#172435",
            },
        },
    )


@router.get("/portal")
def portal() -> RedirectResponse:
    return RedirectResponse("/", status_code=303)


@router.post("/finance-records")
async def submit_finance_record(request: Request, db: Session = Depends(get_db)):
    user = get_session_user(request)
    if not user:
        return RedirectResponse("/login", status_code=303)
    form = await request.form()
    title = str(form.get("title", "")).strip()
    description = str(form.get("description", "")).strip()
    category = str(form.get("category", "")).strip()
    if not title or not description or not category:
        return RedirectResponse("/", status_code=303)
    amount_raw = str(form.get("amount", "")).strip()
    try:
        payload = FinanceRecordCreate(
            record_type=str(form.get("record_type", "decision")),
            title=title,
            description=description,
            category=category,
            flow_direction=str(form.get("flow_direction", "neutral")),
            planning_status=str(form.get("planning_status", "planned")),
            risk_level=str(form.get("risk_level", "medium")),
            amount=float(amount_raw) if amount_raw else None,
            currency=str(form.get("currency", "CNY")).strip() or "CNY",
            account_name=str(form.get("account_name", "")).strip() or None,
            counterparty=str(form.get("counterparty", "")).strip() or None,
            due_on=str(form.get("due_on", "")).strip() or None,
            recurrence_rule=str(form.get("recurrence_rule", "")).strip() or None,
            follow_up_action=str(form.get("follow_up_action", "")).strip() or None,
            agent_note=str(form.get("agent_note", "")).strip() or None,
        )
    except (ValidationError, ValueError):
        return RedirectResponse("/", status_code=303)
    create_finance_record(db, payload=payload, actor=user["username"], actor_role=user["role"])
    return RedirectResponse("/", status_code=303)
