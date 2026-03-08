from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from benvinyl_api.db.session import get_db
from benvinyl_api.schemas.dashboard import DashboardSnapshot
from benvinyl_api.services.vinyl_room import build_dashboard_snapshot

router = APIRouter(tags=["dashboard"])


@router.get("/dashboard", response_model=DashboardSnapshot)
def get_dashboard(
    record_id: int | None = Query(default=None),
    db: Session = Depends(get_db),
) -> DashboardSnapshot:
    return build_dashboard_snapshot(db, active_record_id=record_id)
