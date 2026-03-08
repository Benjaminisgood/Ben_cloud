
from __future__ import annotations

from pydantic import BaseModel, Field


class SummaryMetric(BaseModel):
    label: str
    value: str
    hint: str


class DeskPhotoCard(BaseModel):
    id: int
    title: str
    caption: str
    image_url: str
    source_label: str
    added_by: str
    x_pct: float
    y_px: int
    rotation_deg: int
    z_index: int
    accent: str
    tape_offset_pct: int
    animation_delay_ms: int


class TrashPhotoCard(BaseModel):
    id: int
    title: str
    caption: str
    image_url: str
    tossed_at_label: str


class DashboardSnapshot(BaseModel):
    source: str
    display_date: str
    daily_limit: int
    summary: list[SummaryMetric] = Field(default_factory=list)
    desk_cards: list[DeskPhotoCard] = Field(default_factory=list)
    trash_cards: list[TrashPhotoCard] = Field(default_factory=list)
    empty_desk_message: str
    empty_trash_message: str
    add_photo_hint: str
    tips: list[str] = Field(default_factory=list)
