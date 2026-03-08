from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class MetricCard(BaseModel):
    label: str
    value: str
    hint: str


class ViewerState(BaseModel):
    username: str | None
    role: str
    is_admin: bool


class ProgramVideo(BaseModel):
    id: int
    title: str
    summary: str | None
    asset_url: str
    poster_url: str | None
    duration_label: str | None
    reel_label: str
    restored_today: bool


class TrashVideo(BaseModel):
    id: int
    title: str
    summary: str | None
    poster_url: str | None
    trashed_at: datetime | None


class DashboardSnapshot(BaseModel):
    source: str
    day_label: str
    summary: list[MetricCard]
    program: list[ProgramVideo]
    trash: list[TrashVideo]
    viewer: ViewerState
