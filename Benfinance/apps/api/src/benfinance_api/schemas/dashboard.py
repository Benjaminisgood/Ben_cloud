
from __future__ import annotations

from pydantic import BaseModel


class DashboardMetric(BaseModel):
    label: str
    value: str
    hint: str


class DashboardColumn(BaseModel):
    key: str
    label: str


class DashboardTable(BaseModel):
    title: str
    subtitle: str
    empty_message: str
    columns: list[DashboardColumn]
    rows: list[dict[str, str]]


class DashboardSnapshot(BaseModel):
    source: str
    summary: list[DashboardMetric]
    collections: list[DashboardTable]
