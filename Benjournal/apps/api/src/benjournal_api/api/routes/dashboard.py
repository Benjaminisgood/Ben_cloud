
from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends

from benjournal_api.api.deps import require_user
from benjournal_api.schemas.dashboard import DashboardSnapshot
from benjournal_api.db.session import get_db
from benjournal_api.services.journal_dashboard import build_dashboard_snapshot
from sqlalchemy.orm import Session

router = APIRouter(tags=["dashboard"])


@router.get("/dashboard", response_model=DashboardSnapshot)
def dashboard(
    selected_date: date | None = None,
    _: dict[str, str] = Depends(require_user),
    db: Session = Depends(get_db),
) -> DashboardSnapshot:
    return build_dashboard_snapshot(db, selected_date=selected_date)
