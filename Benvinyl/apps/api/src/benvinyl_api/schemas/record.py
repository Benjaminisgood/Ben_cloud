from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, Field


class VinylRecordCreate(BaseModel):
    title: str = Field(default="", max_length=120)
    note: str = Field(default="", max_length=2000)
    oss_path: str = Field(min_length=1, max_length=1024)


class VinylRecordUpdate(BaseModel):
    is_trashed: bool | None = None


class VinylRecordRead(BaseModel):
    id: int
    title: str
    note: str
    oss_path: str
    audio_url: str
    added_by: str
    is_trashed: bool
    selected_for_date: date | None
    tossed_at: datetime | None
    created_at: datetime
    updated_at: datetime
