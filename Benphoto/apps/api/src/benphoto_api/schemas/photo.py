
from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, Field, field_validator


class PhotoCreate(BaseModel):
    title: str = Field(default="", max_length=120)
    caption: str = Field(default="", max_length=500)
    oss_path: str = Field(min_length=1, max_length=1024)


    @field_validator("title", "caption", "oss_path", mode="before")
    @classmethod
    def normalize_text(cls, value: object) -> str:
        if value is None:
            return ""
        return str(value).strip()


    @field_validator("oss_path")
    @classmethod
    def ensure_oss_path(cls, value: str) -> str:
        if not value:
            raise ValueError("oss_path_required")
        return value


class PhotoUpdate(BaseModel):
    is_trashed: bool


class PhotoRead(BaseModel):
    id: int
    title: str
    caption: str
    oss_path: str
    image_url: str
    added_by: str
    is_trashed: bool
    selected_for_date: date | None
    tossed_at: datetime | None
    created_at: datetime
    updated_at: datetime
