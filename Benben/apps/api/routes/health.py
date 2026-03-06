from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from ...core.config import get_settings

router = APIRouter(tags=["health"])


def _check_audit_log_writable() -> bool:
    settings = get_settings()
    probe_path = settings.audit_log_path.parent / ".benben_ready_probe"
    try:
        settings.audit_log_path.parent.mkdir(parents=True, exist_ok=True)
        probe_path.write_text("ok", encoding="utf-8")
        probe_path.unlink(missing_ok=True)
        return True
    except OSError:
        return False


@router.get("/health")
async def health() -> dict[str, str]:
    settings = get_settings()
    return {
        "status": "ok",
        "app": settings.app_name,
        "env": settings.app_env,
        "time": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/health/live")
async def health_live() -> dict[str, str]:
    return {"status": "live"}


@router.get("/health/ready")
async def health_ready():
    settings = get_settings()
    checks = {
        "config_loaded": True,
        "audit_log_dir_writable": _check_audit_log_writable(),
        "oss_config_present": bool(settings.oss_endpoint and settings.oss_bucket_name),
    }
    ready = all(checks.values())
    payload = {
        "status": "ready" if ready else "not_ready",
        "checks": checks,
    }
    return JSONResponse(status_code=200 if ready else 503, content=payload)
