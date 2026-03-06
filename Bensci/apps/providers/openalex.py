from __future__ import annotations

from typing import Any

from apps.providers.base import ProviderQuery, ProviderRecord
from apps.providers.http import HttpProviderMixin


def _reconstruct_abstract(index: dict[str, list[int]] | None) -> str:
    if not index:
        return ""
    max_pos = max((max(pos) for pos in index.values() if pos), default=-1)
    if max_pos < 0:
        return ""
    tokens = [""] * (max_pos + 1)
    for word, positions in index.items():
        for pos in positions:
            if 0 <= pos < len(tokens):
                tokens[pos] = word
    return " ".join(token for token in tokens if token).strip()


class OpenAlexProvider(HttpProviderMixin):
    key = "openalex"
    title = "OpenAlex"
    description = "开放学术图谱，包含作者机构与概念标签。"

    def is_configured(self) -> bool:
        return True

    def search(self, query: ProviderQuery, max_results: int) -> list[ProviderRecord]:
        url = "https://api.openalex.org/works"
        per_page = min(200, max(25, max_results if max_results < 200 else 200))
        page = 1
        records: list[ProviderRecord] = []

        while len(records) < max_results:
            params = {
                "page": page,
                "per_page": per_page,
            }
            if query.query_field == "filter":
                filter_parts = [query.compiled_query, "is_paratext:false"]
                params["filter"] = ",".join(part for part in filter_parts if part)
            else:
                params[query.query_field] = query.compiled_query
                params["filter"] = "is_paratext:false"
            response = self._get(url, params=params)
            if response.status_code != 200:
                break

            payload = response.json()
            results = payload.get("results") or []
            if not results:
                break

            for item in results:
                doi = str(item.get("doi") or "").replace("https://doi.org/", "").strip()
                if not doi:
                    continue

                authorships = item.get("authorships") or []
                corresponding = ""
                affiliations: list[str] = []
                for authorship in authorships:
                    author = authorship.get("author") or {}
                    name = str(author.get("display_name") or "").strip()
                    if authorship.get("is_corresponding") and name and not corresponding:
                        corresponding = name

                    for institution in authorship.get("institutions") or []:
                        inst_name = str((institution or {}).get("display_name") or "").strip()
                        if inst_name:
                            affiliations.append(inst_name)

                if not corresponding and authorships:
                    first_author = (authorships[0].get("author") or {}).get("display_name")
                    corresponding = str(first_author or "").strip()

                host = item.get("host_venue") or {}
                primary_location = item.get("primary_location") or {}
                source = primary_location.get("source") or {}

                biblio = item.get("biblio") or {}
                first_page = str(biblio.get("first_page") or "").strip()
                last_page = str(biblio.get("last_page") or "").strip()
                _pages = ""
                if first_page and last_page:
                    _pages = f"{first_page}-{last_page}"
                else:
                    _pages = first_page or last_page

                keywords = [
                    str((concept or {}).get("display_name") or "").strip()
                    for concept in item.get("concepts") or []
                    if (concept or {}).get("display_name")
                ]

                records.append(
                    ProviderRecord(
                        doi=doi,
                        title=str(item.get("title") or "").strip(),
                        keywords=keywords,
                        abstract=_reconstruct_abstract(item.get("abstract_inverted_index")),
                        journal=str(host.get("display_name") or "").strip(),
                        corresponding_author=corresponding,
                        affiliations=affiliations,
                        source=self.key,
                        publisher=str(host.get("publisher") or "").strip(),
                        published_date=str(item.get("publication_date") or item.get("publication_year") or "").strip(),
                        url=str(primary_location.get("landing_page_url") or source.get("host_page_url") or item.get("id") or "").strip(),
                        citation_count=(
                            int(item.get("cited_by_count"))
                            if item.get("cited_by_count") is not None
                            else None
                        ),
                    )
                )
                if len(records) >= max_results:
                    break

            if len(results) < per_page:
                break
            page += 1
            self._sleep()

        return records
