from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict

VideoItemStatus = Literal["active", "trashed"]


class VideoItemStatusUpdate(BaseModel):
    status: VideoItemStatus


class VideoItemRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    external_id: str
    title: str
    asset_url: str
    poster_url: str | None
    summary: str | None
    duration_label: str | None
    library_order: int
    status: VideoItemStatus
    trashed_at: datetime | None
    trashed_by: str | None
    restored_at: datetime | None
    restored_by: str | None
    created_at: datetime
    updated_at: datetime
