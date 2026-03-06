"""Top-level web router for HTML pages."""

from fastapi import APIRouter

from .routes import auth, pages, sso

web_router = APIRouter()
web_router.include_router(auth.router)
web_router.include_router(pages.router)
web_router.include_router(sso.router)
