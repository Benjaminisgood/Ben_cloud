
from __future__ import annotations

from fastapi import APIRouter

from .routes import auth, pages

router = APIRouter()
router.include_router(auth.router)
router.include_router(pages.router)
