from __future__ import annotations

from datetime import date, datetime
from typing import List, Optional

from pydantic import BaseModel, Field

from .property_media import PropertyMediaOut


class PropertyCreateRequest(BaseModel):
    title: str = Field(min_length=1, max_length=120)
    description: str = ""
    city: str = ""
    address: str = ""
    price_per_night: int = Field(gt=0)
    max_guests: int = Field(gt=0)
    is_active: bool = True


class PropertyPatchRequest(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=120)
    description: str | None = None
    city: str | None = None
    address: str | None = None
    price_per_night: int | None = Field(default=None, gt=0)
    max_guests: int | None = Field(default=None, gt=0)
    is_active: bool | None = None


class PropertyOut(BaseModel):
    id: int
    title: str
    description: str
    city: str
    address: str
    price_per_night: int
    max_guests: int
    is_active: bool
    created_by_admin_id: int
    created_at: datetime
    updated_at: datetime
    # 媒体资源（可选，用于详情接口）
    media: Optional[List[PropertyMediaOut]] = None


class PropertyAvailabilityOut(BaseModel):
    property_id: int
    check_in_date: date
    check_out_date: date
    total_nights: int
    available: bool
    conflict_dates: list[date]
