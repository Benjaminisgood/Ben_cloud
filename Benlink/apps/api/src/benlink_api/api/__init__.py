"""Benlink API routers."""
from benlink_api.api.health import router as health_router
from benlink_api.api.links import router as links_router

__all__ = ["health_router", "links_router"]
