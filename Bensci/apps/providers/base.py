from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol

from apps.services.normalizers import normalize_doi, normalize_list


@dataclass(slots=True)
class ProviderRecord:
    doi: str = ""
    title: str = ""
    keywords: list[str] = field(default_factory=list)
    abstract: str = ""
    journal: str = ""
    corresponding_author: str = ""
    affiliations: list[str] = field(default_factory=list)
    source: str = ""
    publisher: str = ""
    published_date: str = ""
    url: str = ""
    citation_count: int | None = None
    impact_factor: float | None = None

    def dedup_key(self) -> str:
        return normalize_doi(self.doi)


@dataclass(slots=True)
class ProviderQuery:
    provider: str
    raw_query: str
    compiled_query: str
    query_field: str = "query"
    query_contexts: list[str] = field(default_factory=list)
    domain_scope_name: str = ""
    domain_scope_reason: str = ""
    domain_scope_terms: list[str] = field(default_factory=list)


class MetadataProvider(Protocol):
    key: str
    title: str
    description: str

    def is_configured(self) -> bool:
        ...

    def search(self, query: ProviderQuery, max_results: int) -> list[ProviderRecord]:
        ...


def merge_records(primary: ProviderRecord, fallback: ProviderRecord) -> ProviderRecord:
    primary_keywords = normalize_list(primary.keywords)
    fallback_keywords = normalize_list(fallback.keywords)
    merged_keywords = normalize_list(primary_keywords + fallback_keywords)

    primary_aff = normalize_list(primary.affiliations)
    fallback_aff = normalize_list(fallback.affiliations)
    merged_aff = normalize_list(primary_aff + fallback_aff)

    primary_abs = primary.abstract or ""
    fallback_abs = fallback.abstract or ""
    best_abstract = primary_abs if len(primary_abs) >= len(fallback_abs) else fallback_abs

    return ProviderRecord(
        doi=primary.doi or fallback.doi,
        title=primary.title or fallback.title,
        keywords=merged_keywords,
        abstract=best_abstract,
        journal=primary.journal or fallback.journal,
        corresponding_author=primary.corresponding_author or fallback.corresponding_author,
        affiliations=merged_aff,
        source=primary.source or fallback.source,
        publisher=primary.publisher or fallback.publisher,
        published_date=primary.published_date or fallback.published_date,
        url=primary.url or fallback.url,
        citation_count=max(
            primary.citation_count if primary.citation_count is not None else -1,
            fallback.citation_count if fallback.citation_count is not None else -1,
        )
        if (primary.citation_count is not None or fallback.citation_count is not None)
        else None,
        impact_factor=max(
            primary.impact_factor if primary.impact_factor is not None else -1.0,
            fallback.impact_factor if fallback.impact_factor is not None else -1.0,
        )
        if (primary.impact_factor is not None or fallback.impact_factor is not None)
        else None,
    )
