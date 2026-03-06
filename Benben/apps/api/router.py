from __future__ import annotations

from fastapi import APIRouter

from .routes import auth, editor, health

router = APIRouter()
router.include_router(health.router)
router.include_router(auth.router)
router.include_router(editor.router)
