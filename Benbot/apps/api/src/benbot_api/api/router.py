from __future__ import annotations

from fastapi import APIRouter

from .routes import admin_users, bug_repair, bugs, projects

api_router = APIRouter(prefix="/api")
api_router.include_router(projects.router)
api_router.include_router(bugs.router)
api_router.include_router(bug_repair.router)
api_router.include_router(admin_users.router)
