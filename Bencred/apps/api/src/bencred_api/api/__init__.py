"""Bencred API routers."""
from bencred_api.api.credentials import router as credentials_router
from bencred_api.api.health import router as health_router

__all__ = ["credentials_router", "health_router"]
