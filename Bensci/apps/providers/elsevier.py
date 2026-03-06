from __future__ import annotations

from apps.core.config import settings
from apps.providers.base import ProviderQuery, ProviderRecord
from apps.providers.http import HttpProviderMixin


class ElsevierProvider(HttpProviderMixin):
    key = "elsevier"
    title = "Elsevier / Scopus"
    description = "Scopus 检索，覆盖化学与催化期刊丰富。"

    def is_configured(self) -> bool:
        return bool(settings.elsevier_api_key)

    def search(self, query: ProviderQuery, max_results: int) -> list[ProviderRecord]:
        if not self.is_configured():
            return []

        page_size = min(25, max_results)
        start = 0
        records: list[ProviderRecord] = []
        seen: set[str] = set()

        while len(records) < max_results:
            params = {
                "query": query.compiled_query,
                "count": page_size,
                "start": start,
                "view": "COMPLETE",
            }
            response = self._get(
                "https://api.elsevier.com/content/search/scopus",
                params=params,
                headers={"X-ELS-APIKey": settings.elsevier_api_key, "Accept": "application/json"},
            )
            if response.status_code != 200:
                break

            payload = response.json()
            entries = ((payload or {}).get("search-results") or {}).get("entry") or []
            if not entries:
                break

            for entry in entries:
                doi = str(entry.get("prism:doi") or "").strip()
                if not doi:
                    continue
                if doi.lower() in seen:
                    continue
                seen.add(doi.lower())

                authors_raw = entry.get("dc:creator")
                if isinstance(authors_raw, list):
                    authors = [str(item).strip() for item in authors_raw if str(item).strip()]
                elif isinstance(authors_raw, str) and authors_raw.strip():
                    authors = [authors_raw.strip()]
                else:
                    authors = []

                keywords_raw = entry.get("authkeywords") or entry.get("dc:subject") or ""
                keywords: list[str]
                if isinstance(keywords_raw, list):
                    keywords = [str(item).strip() for item in keywords_raw if str(item).strip()]
                elif isinstance(keywords_raw, dict):
                    values = keywords_raw.get("author-keyword") or keywords_raw.get("subject") or []
                    if isinstance(values, list):
                        keywords = [str(item).strip() for item in values if str(item).strip()]
                    else:
                        text = str(values or "").strip()
                        keywords = [text] if text else []
                else:
                    text = str(keywords_raw or "").strip()
                    keywords = [text] if text else []

                records.append(
                    ProviderRecord(
                        doi=doi,
                        title=str(entry.get("dc:title") or "").strip(),
                        keywords=keywords,
                        abstract=str(entry.get("dc:description") or "").strip(),
                        journal=str(entry.get("prism:publicationName") or "").strip(),
                        corresponding_author=authors[0] if authors else "",
                        affiliations=[],
                        source=self.key,
                        publisher=str(entry.get("dc:publisher") or "").strip(),
                        published_date=str(entry.get("prism:coverDate") or "").strip(),
                        url=str(entry.get("prism:url") or "").strip(),
                        citation_count=(
                            int(entry.get("citedby-count"))
                            if entry.get("citedby-count") not in (None, "")
                            else None
                        ),
                    )
                )

                if len(records) >= max_results:
                    break

            if len(entries) < page_size:
                break
            start += page_size
            self._sleep()

        return records[:max_results]
