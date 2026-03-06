from __future__ import annotations

from apps.providers.arxiv import ArxivProvider
from apps.providers.base import MetadataProvider
from apps.providers.crossref import CrossrefProvider
from apps.providers.elsevier import ElsevierProvider
from apps.providers.openalex import OpenAlexProvider
from apps.providers.pubmed import PubMedProvider
from apps.providers.springer import SpringerProvider


def get_all_providers() -> dict[str, MetadataProvider]:
    providers: list[MetadataProvider] = [
        CrossrefProvider(),
        OpenAlexProvider(),
        PubMedProvider(),
        SpringerProvider(),
        ElsevierProvider(),
        ArxivProvider(),
    ]
    return {provider.key: provider for provider in providers}
