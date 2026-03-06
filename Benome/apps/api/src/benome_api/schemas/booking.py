from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field


class BookingCreateRequest(BaseModel):
    property_id: int
    check_in_date: date
    check_out_date: date
    guest_count: int = Field(gt=0)
    guest_name: str = Field(min_length=1, max_length=80)
    guest_phone: str = Field(min_length=1, max_length=40)
    note: str = ""


class BookingReviewRequest(BaseModel):
    approve: bool
    payment_received: bool = False
    review_note: str = ""


class BookingOut(BaseModel):
    id: int
    property_id: int
    customer_id: int | None
    check_in_date: date
    check_out_date: date
    total_nights: int
    guest_count: int
    guest_name: str
    guest_phone: str
    note: str
    status: str
    payment_received: bool
    payment_confirmed_at: datetime | None
    review_note: str
    reviewed_by_admin_id: int | None
    reviewed_at: datetime | None
    created_at: datetime
    updated_at: datetime


class BookingDetailOut(BookingOut):
    """增强的预订详情响应，包含房源信息"""
    property_title: str | None = None
    property_address: str | None = None
    property_cover: str | None = None
    price_per_night: int | None = None
    total_price: int | None = None

    model_config = ConfigDict(from_attributes=True)
