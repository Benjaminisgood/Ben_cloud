from __future__ import annotations

from fastapi import APIRouter

from .routes import auth, pages

web_router = APIRouter()
web_router.include_router(auth.router)
web_router.include_router(pages.router)
