from __future__ import annotations

from fastapi import APIRouter

from .routes import pages

web_router = APIRouter()
web_router.include_router(pages.router)
