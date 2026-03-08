
from __future__ import annotations

from fastapi import APIRouter

from benhealth_api.core.config import get_settings

from .routes import dashboard, health_records, system

router = APIRouter(prefix=get_settings().API_PREFIX)
router.include_router(system.router)
router.include_router(dashboard.router)
router.include_router(health_records.router)
