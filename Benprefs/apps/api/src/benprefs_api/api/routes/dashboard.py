
from __future__ import annotations

from fastapi import APIRouter, Depends

from benprefs_api.api.deps import require_user
from benprefs_api.core.config import get_settings
from benprefs_api.schemas.dashboard import DashboardSnapshot
from benprefs_api.services.legacy_data import get_dashboard_snapshot

router = APIRouter(tags=["dashboard"])


@router.get("/dashboard", response_model=DashboardSnapshot)
def dashboard(_: dict[str, str] = Depends(require_user)) -> DashboardSnapshot:
    settings = get_settings()
    return get_dashboard_snapshot(settings.SOURCE_DATABASE_PATH)
