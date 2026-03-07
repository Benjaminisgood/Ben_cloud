from __future__ import annotations

from fastapi import APIRouter

from benome_api.core.config import get_settings

from .routes import auth, bookings, properties, property_media, users, statistics, system

settings = get_settings()

api_router = APIRouter(prefix=settings.API_PREFIX)
api_router.include_router(auth.router)
api_router.include_router(properties.router)
api_router.include_router(bookings.router)
api_router.include_router(property_media.router)
api_router.include_router(users.router)
api_router.include_router(statistics.router)
api_router.include_router(system.router)
