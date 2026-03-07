from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/metadata")
def metadata_legacy() -> dict[str, object]:
    """Backward-compatible endpoint kept for old callers of /api/metadata."""
    return {
        "service": "CATAPEDIA Metadata Service",
        "status": "ok",
        "api_prefix": "/api",
        "docs": "/docs",
        "health": "/api/health",
    }
