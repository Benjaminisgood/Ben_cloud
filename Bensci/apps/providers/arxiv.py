from __future__ import annotations

import re
import xml.etree.ElementTree as ET

from apps.providers.base import ProviderQuery, ProviderRecord
from apps.providers.http import HttpProviderMixin


class ArxivProvider(HttpProviderMixin):
    key = "arxiv"
    title = "arXiv"
    description = "预印本补充源，作为正式期刊之外的前沿补集。"

    def is_configured(self) -> bool:
        return True

    @staticmethod
    def _ns(tag: str) -> str:
        return f"{{http://www.w3.org/2005/Atom}}{tag}"

    def search(self, query: ProviderQuery, max_results: int) -> list[ProviderRecord]:
        url = "http://export.arxiv.org/api/query"
        page_size = min(100, max_results)
        start = 0
        records: list[ProviderRecord] = []

        while len(records) < max_results:
            search_query = query.compiled_query
            if search_query and not re.search(r"\b(?:ti|abs|au|co|jr|cat|rn|all):", search_query):
                search_query = f"all:{search_query}"

            params = {
                "search_query": search_query,
                "start": start,
                "max_results": page_size,
                "sortBy": "relevance",
            }
            response = self._get(url, params=params)
            if response.status_code != 200:
                break

            root = ET.fromstring(response.text)
            entries = root.findall(self._ns("entry"))
            if not entries:
                break

            for entry in entries:
                entry_id = (entry.findtext(self._ns("id"), default="") or "").strip()
                arxiv_id = entry_id.rstrip("/").split("/")[-1] if entry_id else ""
                doi = f"arxiv:{arxiv_id}" if arxiv_id else ""
                if not doi:
                    continue

                authors: list[str] = []
                for author in entry.findall(self._ns("author")):
                    name = (author.findtext(self._ns("name"), default="") or "").strip()
                    if name:
                        authors.append(name)

                categories = [
                    (cat.attrib.get("term", "") or "").strip()
                    for cat in entry.findall(self._ns("category"))
                ]

                published = (entry.findtext(self._ns("published"), default="") or "").strip()
                records.append(
                    ProviderRecord(
                        doi=doi,
                        title=(entry.findtext(self._ns("title"), default="") or "").strip(),
                        keywords=[item for item in categories if item],
                        abstract=(entry.findtext(self._ns("summary"), default="") or "").strip(),
                        journal="arXiv",
                        corresponding_author=authors[0] if authors else "",
                        affiliations=[],
                        source=self.key,
                        publisher="arXiv",
                        published_date=published[:10] if published else "",
                        url=entry_id,
                    )
                )
                if len(records) >= max_results:
                    break

            if len(entries) < page_size:
                break
            start += page_size
            self._sleep()

        return records[:max_results]
