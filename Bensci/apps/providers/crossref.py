from __future__ import annotations

import re
from typing import Any

from apps.providers.base import ProviderQuery, ProviderRecord
from apps.providers.http import HttpProviderMixin


class CrossrefProvider(HttpProviderMixin):
    key = "crossref"
    title = "Crossref"
    description = "跨出版商 DOI 元数据，覆盖广，适合化学文献补全。"

    def is_configured(self) -> bool:
        return True

    @staticmethod
    def _pick_date(item: dict[str, Any]) -> str:
        for key in ("published-print", "published-online", "issued", "created"):
            node = item.get(key) or {}
            parts = node.get("date-parts") or []
            if parts and isinstance(parts[0], list):
                return "-".join(str(x) for x in parts[0])
        return ""

    @staticmethod
    def _clean_abstract(text: str) -> str:
        if not text:
            return ""
        return re.sub(r"<[^>]+>", "", text).strip()

    def search(self, query: ProviderQuery, max_results: int) -> list[ProviderRecord]:
        url = "https://api.crossref.org/works"
        rows = min(100, max_results)
        offset = 0
        records: list[ProviderRecord] = []

        while len(records) < max_results:
            params = {query.query_field: query.compiled_query, "rows": rows, "offset": offset}
            response = self._get(url, params=params)
            if response.status_code != 200:
                break

            payload = response.json()
            items = ((payload or {}).get("message") or {}).get("items") or []
            if not items:
                break

            for item in items:
                doi = str(item.get("DOI") or "").strip()
                if not doi:
                    continue

                title = ""
                title_list = item.get("title") or []
                if title_list:
                    title = str(title_list[0]).strip()

                journal = ""
                container = item.get("container-title") or []
                if container:
                    journal = str(container[0]).strip()

                author_names: list[str] = []
                affiliations: list[str] = []
                corresponding = ""
                for author in item.get("author") or []:
                    given = str(author.get("given") or "").strip()
                    family = str(author.get("family") or "").strip()
                    full_name = " ".join(part for part in (given, family) if part).strip()
                    if not full_name:
                        full_name = str(author.get("name") or "").strip()
                    if full_name:
                        author_names.append(full_name)
                    if not corresponding and author.get("sequence") == "first":
                        corresponding = full_name

                    for aff in author.get("affiliation") or []:
                        name = str((aff or {}).get("name") or "").strip()
                        if name:
                            affiliations.append(name)

                subjects = [str(v).strip() for v in (item.get("subject") or []) if str(v).strip()]

                records.append(
                    ProviderRecord(
                        doi=doi,
                        title=title,
                        keywords=subjects,
                        abstract=self._clean_abstract(str(item.get("abstract") or "")),
                        journal=journal,
                        corresponding_author=corresponding,
                        affiliations=affiliations,
                        source=self.key,
                        publisher=str(item.get("publisher") or "").strip(),
                        published_date=self._pick_date(item),
                        url=str(item.get("URL") or "").strip(),
                        citation_count=(
                            int(item.get("is-referenced-by-count"))
                            if item.get("is-referenced-by-count") is not None
                            else None
                        ),
                    )
                )

                if len(records) >= max_results:
                    break

            if len(items) < rows:
                break
            offset += rows
            self._sleep()

        return records
