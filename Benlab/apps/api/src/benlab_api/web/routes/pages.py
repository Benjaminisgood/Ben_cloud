"""Aggregated non-auth web page routes."""

from fastapi import APIRouter

from . import events, items, locations, members, misc

router = APIRouter(tags=["pages"])
router.include_router(misc.router)
router.include_router(items.router)
router.include_router(locations.router)
router.include_router(events.router)
router.include_router(members.router)
