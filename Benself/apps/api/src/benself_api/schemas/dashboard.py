from __future__ import annotations

from pydantic import BaseModel


class DashboardMetric(BaseModel):
    label: str
    value: str
    hint: str


class RawJournalFact(BaseModel):
    id: int
    date: str
    title: str
    mood: str
    current_state: str
    thoughts: str
    focus_areas: str
    tags: str
    word_count: int


class ConfirmedFact(BaseModel):
    title: str
    detail: str
    fact_date: str
    source_label: str


class ConfirmedFactDomain(BaseModel):
    id: str
    icon: str
    title: str
    subtitle: str
    facts: list[ConfirmedFact]


class AgentContextPreview(BaseModel):
    narrative: str
    confirmed_facts: list[str]
    recent_signals: list[str]
    suggested_prompts: list[str]
    prompt_block: str


class GraphitiStatus(BaseModel):
    enabled: bool
    ready: bool
    backend: str
    sync_hint: str


class DashboardSnapshot(BaseModel):
    summary: list[DashboardMetric]
    raw_journals: list[RawJournalFact]
    confirmed_domains: list[ConfirmedFactDomain]
    agent_context: AgentContextPreview
    graphiti: GraphitiStatus
