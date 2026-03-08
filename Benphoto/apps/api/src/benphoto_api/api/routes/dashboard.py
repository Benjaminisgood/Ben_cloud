
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from benphoto_api.api.deps import require_user
from benphoto_api.db.session import get_db
from benphoto_api.schemas.dashboard import DashboardSnapshot
from benphoto_api.services.photo_desk import build_dashboard_snapshot

router = APIRouter(tags=["dashboard"])


@router.get("/dashboard", response_model=DashboardSnapshot)
def dashboard(
    _: dict[str, str] = Depends(require_user),
    db: Session = Depends(get_db),
) -> DashboardSnapshot:
    return build_dashboard_snapshot(db)
