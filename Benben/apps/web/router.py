from __future__ import annotations

from fastapi import APIRouter

from .routes import pages

router = APIRouter()
router.include_router(pages.router)
