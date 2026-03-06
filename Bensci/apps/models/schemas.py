from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

CheckStatus = Literal["unchecked", "correct", "error"]
TagMatchMode = Literal["or", "and"]
QueryFilterMode = Literal["none", "embedding", "boolean", "llm"]


class TagRead(BaseModel):
    id: int
    name: str
    article_count: int = 0

    model_config = {"from_attributes": True}


class ArticleBase(BaseModel):
    doi: str = Field(min_length=3, max_length=255)
    title: str = ""
    keywords: list[str] = Field(default_factory=list)
    abstract: str = ""
    journal: str = ""
    corresponding_author: str = ""
    affiliations: list[str] = Field(default_factory=list)
    source: str = ""
    publisher: str = ""
    published_date: str = ""
    url: str = ""
    note: str = ""
    check_status: CheckStatus = "unchecked"
    citation_count: int | None = Field(default=None, ge=0)
    impact_factor: float | None = Field(default=None, ge=0)
    tags: list[str] = Field(default_factory=list)


class ArticleCreate(ArticleBase):
    pass


class ArticleUpdate(BaseModel):
    title: str | None = None
    keywords: list[str] | None = None
    abstract: str | None = None
    journal: str | None = None
    corresponding_author: str | None = None
    affiliations: list[str] | None = None
    source: str | None = None
    publisher: str | None = None
    published_date: str | None = None
    url: str | None = None
    note: str | None = None
    check_status: CheckStatus | None = None
    citation_count: int | None = Field(default=None, ge=0)
    impact_factor: float | None = Field(default=None, ge=0)
    tags: list[str] | None = None


class ArticleRead(BaseModel):
    id: int
    doi: str
    title: str
    keywords: list[str]
    abstract: str
    journal: str
    corresponding_author: str
    affiliations: list[str]
    source: str
    publisher: str
    published_date: str
    url: str
    note: str
    check_status: CheckStatus
    citation_count: int | None = None
    impact_factor: float | None = None
    ingested_at: datetime
    tags: list[TagRead]
    created_at: datetime
    updated_at: datetime


class QuickArticleCreate(BaseModel):
    doi: str = Field(min_length=3, max_length=255)
    tags: list[str] = Field(default_factory=list)
    note: str = ""
    run_enrichment: bool = True
    include_embedding: bool = False


class QuickArticleCreateResponse(BaseModel):
    article: ArticleRead
    enrichment_job_id: str | None = None
    logs: list[str] = Field(default_factory=list)
    enrichment_result: dict | None = None


class ArticleListResponse(BaseModel):
    total: int
    items: list[ArticleRead]


class ArticleTagUpdate(BaseModel):
    tags: list[str] = Field(default_factory=list)


class ProviderRead(BaseModel):
    key: str
    title: str
    configured: bool
    description: str


class IngestRequest(BaseModel):
    query: str | None = None
    max_results: int = Field(default=200, ge=1, le=5000)
    providers: list[str] | None = None
    save_tags: list[str] = Field(default_factory=list)
    query_filter_mode: QueryFilterMode = "embedding"
    query_similarity_threshold: float = Field(default=0.35, ge=0, le=1)
    llm_scoring_prompt: str | None = None
    llm_review_existing_articles: bool = False
    llm_review_dropped_articles: bool = False
    published_from: str | None = None
    published_to: str | None = None
    required_keywords: list[str] = Field(default_factory=list)
    optional_keywords: list[str] = Field(default_factory=list)
    excluded_keywords: list[str] = Field(default_factory=list)
    journal_whitelist: list[str] = Field(default_factory=list)
    journal_blacklist: list[str] = Field(default_factory=list)
    min_citation_count: int | None = Field(default=None, ge=0)
    min_impact_factor: float | None = Field(default=None, ge=0)


class ProviderStats(BaseModel):
    provider: str
    fetched: int
    merged: int
    errors: list[str] = Field(default_factory=list)


class IngestResponse(BaseModel):
    query: str
    inserted: int
    updated: int
    skipped: int
    merged_unique: int
    provider_stats: list[ProviderStats]


class IngestJobCreateResponse(BaseModel):
    job_id: str
    status: str


class IngestJobStatusResponse(BaseModel):
    job_id: str
    status: str
    logs: list[str] = Field(default_factory=list)
    next_line: int = 0
    result: IngestResponse | None = None
    error: str | None = None
    created_at: datetime
    started_at: datetime | None = None
    finished_at: datetime | None = None


class IngestJobControlResponse(BaseModel):
    job_id: str
    status: str
    message: str = ""
    providers: list[str] = Field(default_factory=list)


class IngestJobProvidersUpdateRequest(BaseModel):
    providers: list[str] = Field(default_factory=list)


class EnrichmentFillRequest(BaseModel):
    limit: int = Field(default=50, ge=1, le=1000)
    workers: int = Field(default=4, ge=1, le=16)


class EnrichmentJobCreateResponse(BaseModel):
    job_id: str
    status: str


class EnrichmentJobStatusResponse(BaseModel):
    job_id: str
    status: str
    logs: list[str] = Field(default_factory=list)
    next_line: int = 0
    result: dict | None = None
    error: str | None = None
    created_at: datetime
    started_at: datetime | None = None
    finished_at: datetime | None = None


class EnrichmentJobControlResponse(BaseModel):
    job_id: str
    status: str
    message: str = ""


class AutoEnrichmentStatusResponse(BaseModel):
    auto_enabled: bool = False
    has_job: bool = False
    job_id: str | None = None
    status: str = "idle"
    logs: list[str] = Field(default_factory=list)
    next_line: int = 0
    result: dict | None = None
    error: str | None = None
    created_at: datetime | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None


class AutoEnrichmentToggleRequest(BaseModel):
    enabled: bool


class AutoEnrichmentToggleResponse(BaseModel):
    enabled: bool
    message: str = ""


class TagCreate(BaseModel):
    name: str = Field(min_length=1, max_length=128)


class TagListResponse(BaseModel):
    total: int
    items: list[TagRead]


class TaskCreateRequest(BaseModel):
    task_type: str = Field(min_length=1, max_length=64)
    payload: dict[str, object] = Field(default_factory=dict)


class TaskCreateResponse(BaseModel):
    task_id: str
    status: str


class TaskSnapshotResponse(BaseModel):
    task_id: str
    task_type: str
    status: str
    payload: dict[str, object] = Field(default_factory=dict)
    result: dict[str, object] = Field(default_factory=dict)
    logs: list[str] = Field(default_factory=list)
    next_line: int = 0
    error: str | None = None
    created_at: datetime
    started_at: datetime | None = None
    finished_at: datetime | None = None
    updated_at: datetime


class TaskListItem(BaseModel):
    task_id: str
    task_type: str
    status: str
    created_at: datetime
    started_at: datetime | None = None
    finished_at: datetime | None = None
    updated_at: datetime


class TaskListResponse(BaseModel):
    total: int
    items: list[TaskListItem]


class DroppedQueryFilterDecisionRead(BaseModel):
    id: int
    doi: str
    article_id: int | None = None
    article_title: str = ""
    decision_scope_hash: str
    decision_scope_text: str = ""
    scope_summary: str = ""
    score: float | None = None
    reason: str = ""
    model_name: str = ""
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    total_tokens: int | None = None
    decided_at: datetime | None = None

    model_config = {"from_attributes": True}


class DroppedQueryFilterDecisionListResponse(BaseModel):
    total: int
    items: list[DroppedQueryFilterDecisionRead]


class DroppedQueryFilterRescueResponse(BaseModel):
    status: str
    doi: str
    decision_scope_hash: str
