from __future__ import annotations

from datetime import datetime
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, field_validator

from ...dependencies import get_current_admin
from ...models import User
from ...services.errors import ServiceError
from ...services.system_settings import (
    get_system_info,
    load_admin_settings,
    save_admin_settings,
)

router = APIRouter(tags=["system"])


class AdminSettingsPayload(BaseModel):
    platform_name: str = Field(min_length=1, max_length=120)
    currency: Literal["CNY", "USD", "EUR"] = "CNY"
    max_advance_days: int = Field(ge=1, le=365)
    min_nights: int = Field(ge=1, le=30)
    check_in_time: str
    check_out_time: str
    email_notifications: Literal["enabled", "disabled"] = "enabled"
    sms_notifications: Literal["enabled", "disabled"] = "enabled"

    @field_validator("check_in_time", "check_out_time")
    @classmethod
    def validate_time(cls, value: str) -> str:
        try:
            datetime.strptime(value, "%H:%M")
        except ValueError as exc:
            raise ValueError("time must be in HH:MM format") from exc
        return value


@router.get("/system/info")
def system_info_api(
    admin: User = Depends(get_current_admin),
):
    del admin
    return get_system_info()


@router.get("/admin/settings")
def get_admin_settings_api(
    admin: User = Depends(get_current_admin),
):
    del admin
    return {"ok": True, "settings": load_admin_settings()}


@router.post("/admin/settings")
def save_admin_settings_api(
    payload: AdminSettingsPayload,
    admin: User = Depends(get_current_admin),
):
    del admin
    try:
        saved = save_admin_settings(payload.model_dump())
    except OSError as exc:
        raise HTTPException(status_code=500, detail="保存设置失败") from exc
    except ServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc
    return {"ok": True, "settings": saved}
