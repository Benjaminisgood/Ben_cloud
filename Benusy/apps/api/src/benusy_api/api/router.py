from __future__ import annotations

from fastapi import APIRouter

from benusy_api.core.config import get_settings

from .routes import admin, assignments, auth, dashboard, public, tasks, users

settings = get_settings()

api_router = APIRouter(prefix=settings.API_PREFIX)
api_router.include_router(auth.router)
api_router.include_router(users.router)
api_router.include_router(tasks.router)
api_router.include_router(assignments.router)
api_router.include_router(admin.router)
api_router.include_router(dashboard.router)
api_router.include_router(public.router)
