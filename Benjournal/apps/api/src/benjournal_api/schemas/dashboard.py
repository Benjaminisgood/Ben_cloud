
from __future__ import annotations

from pydantic import BaseModel, Field

from benjournal_api.schemas.journal_day import JournalDayListItem, JournalDayRead


class SummaryMetric(BaseModel):
    label: str
    value: str
    hint: str


class DashboardSnapshot(BaseModel):
    selected_date: str
    selected_day: JournalDayRead | None = None
    recent_days: list[JournalDayListItem] = Field(default_factory=list)
    summary: list[SummaryMetric] = Field(default_factory=list)
