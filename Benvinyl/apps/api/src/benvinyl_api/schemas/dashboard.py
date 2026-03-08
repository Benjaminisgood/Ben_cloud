from __future__ import annotations

from pydantic import BaseModel, Field


class SummaryMetric(BaseModel):
    label: str
    value: str
    hint: str


class TurntableNowPlaying(BaseModel):
    id: int
    title: str
    note: str
    audio_url: str
    source_label: str


class DeskVinylCard(BaseModel):
    id: int
    title: str
    note: str
    audio_url: str
    source_label: str
    x_pct: float
    y_px: int
    rotation_deg: int
    z_index: int
    label_tone: str
    animation_delay_ms: int
    is_active: bool


class TrashVinylCard(BaseModel):
    id: int
    title: str
    note: str
    tossed_at_label: str


class DashboardSnapshot(BaseModel):
    source: str
    display_date: str
    daily_limit: int
    summary: list[SummaryMetric] = Field(default_factory=list)
    now_playing: TurntableNowPlaying | None = None
    deck_cards: list[DeskVinylCard] = Field(default_factory=list)
    trash_cards: list[TrashVinylCard] = Field(default_factory=list)
    empty_deck_message: str
    empty_trash_message: str
    add_record_hint: str
    tips: list[str] = Field(default_factory=list)
