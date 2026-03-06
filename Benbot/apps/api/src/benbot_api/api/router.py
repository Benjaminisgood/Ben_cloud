from __future__ import annotations

from fastapi import APIRouter

from .routes import bugs, projects, bug_repair

api_router = APIRouter(prefix="/api")
api_router.include_router(projects.router)
api_router.include_router(bugs.router)
api_router.include_router(bug_repair.router)
