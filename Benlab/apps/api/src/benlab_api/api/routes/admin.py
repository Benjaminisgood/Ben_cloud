"""Admin endpoints."""

from pydantic import BaseModel, Field
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ...db.session import get_db
from ...models import Member
from ...services.admin_views import admin_settings_response
from ...utils.runtime_settings import save_admin_settings
from ..deps import require_api_admin

router = APIRouter(tags=["admin"])


class AdminSettingsUpdateRequest(BaseModel):
    values: dict[str, object] = Field(default_factory=dict)
    reset_keys: list[str] = Field(default_factory=list)


@router.get("/admin/settings")
def get_admin_settings(
    user: Member = Depends(require_api_admin),  # noqa: ARG001
    _db: Session = Depends(get_db),  # noqa: ARG001
):
    """Return admin settings."""
    return admin_settings_response()


@router.put("/admin/settings")
def update_admin_settings(
    payload: AdminSettingsUpdateRequest,
    user: Member = Depends(require_api_admin),  # noqa: ARG001
    _db: Session = Depends(get_db),  # noqa: ARG001
):
    """Update admin settings."""
    try:
        save_admin_settings(payload.values, reset_keys=payload.reset_keys)
        return admin_settings_response()
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))
