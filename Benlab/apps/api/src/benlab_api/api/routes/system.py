"""System/status API endpoints."""

from fastapi import APIRouter

router = APIRouter(tags=["system"])


@router.get("/health")
def api_health() -> dict[str, str]:
    return {"status": "ok"}
