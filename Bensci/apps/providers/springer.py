from __future__ import annotations

from apps.core.config import settings
from apps.providers.base import ProviderQuery, ProviderRecord
from apps.providers.http import HttpProviderMixin


class SpringerProvider(HttpProviderMixin):
    key = "springer"
    title = "Springer Nature"
    description = "Springer 元数据接口，含期刊信息与关键词。"

    def is_configured(self) -> bool:
        return bool(settings.springer_meta_api_key)

    @staticmethod
    def _extract_url(record: dict) -> str:
        urls = record.get("url")
        if isinstance(urls, list):
            for node in urls:
                if isinstance(node, dict) and node.get("value"):
                    return str(node.get("value"))
        if isinstance(urls, str):
            return urls
        return ""

    def search(self, query: ProviderQuery, max_results: int) -> list[ProviderRecord]:
        if not self.is_configured():
            return []

        page_size = min(100, max_results)
        start = 1
        records: list[ProviderRecord] = []

        while len(records) < max_results:
            params = {
                "q": query.compiled_query,
                "api_key": settings.springer_meta_api_key,
                "p": page_size,
                "s": start,
            }
            response = self._get(settings.springer_meta_api_base, params=params)
            if response.status_code != 200:
                break

            payload = response.json()
            items = payload.get("records") or []
            if not items:
                break

            for item in items:
                doi = str(item.get("doi") or "").strip()
                if not doi:
                    continue

                creators = item.get("creator")
                creator_names: list[str] = []
                if isinstance(creators, list):
                    creator_names = [str(name).strip() for name in creators if str(name).strip()]
                elif isinstance(creators, str) and creators.strip():
                    creator_names = [creators.strip()]

                subject = item.get("subject") or item.get("keyword") or []
                if isinstance(subject, list):
                    keywords = [str(word).strip() for word in subject if str(word).strip()]
                else:
                    text = str(subject or "").strip()
                    keywords = [text] if text else []

                records.append(
                    ProviderRecord(
                        doi=doi,
                        title=str(item.get("title") or "").strip(),
                        keywords=keywords,
                        abstract=str(item.get("abstractText") or item.get("abstract") or "").strip(),
                        journal=str(item.get("publicationName") or item.get("publication") or "").strip(),
                        corresponding_author=creator_names[0] if creator_names else "",
                        affiliations=[],
                        source=self.key,
                        publisher=str(item.get("publisher") or item.get("publishingCompany") or "").strip(),
                        published_date=str(
                            item.get("publicationDate")
                            or item.get("onlineDate")
                            or item.get("printPublicationDate")
                            or ""
                        ).strip(),
                        url=self._extract_url(item),
                    )
                )

                if len(records) >= max_results:
                    break

            if len(items) < page_size:
                break
            start += page_size
            self._sleep()

        return records[:max_results]
