from __future__ import annotations

import xml.etree.ElementTree as ET

from apps.providers.base import ProviderQuery, ProviderRecord
from apps.providers.http import HttpProviderMixin


class PubMedProvider(HttpProviderMixin):
    key = "pubmed"
    title = "PubMed"
    description = "生物医学数据库，化学催化与能源交叉主题覆盖高。"

    def is_configured(self) -> bool:
        return True

    def _esearch(self, query: str, retmax: int) -> list[str]:
        url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
        params = {"db": "pubmed", "term": query, "retmax": retmax, "retmode": "json"}
        response = self._get(url, params=params)
        if response.status_code != 200:
            return []
        payload = response.json()
        return (((payload or {}).get("esearchresult") or {}).get("idlist") or [])

    def _efetch(self, ids: list[str]) -> list[ProviderRecord]:
        if not ids:
            return []
        url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
        params = {"db": "pubmed", "id": ",".join(ids), "retmode": "xml"}
        response = self._get(url, params=params)
        if response.status_code != 200:
            return []

        root = ET.fromstring(response.text)
        records: list[ProviderRecord] = []
        for article in root.findall("./PubmedArticle"):
            parsed = self._parse_article(article)
            if parsed.doi:
                records.append(parsed)
        return records

    def _parse_article(self, article: ET.Element) -> ProviderRecord:
        medline = article.find("./MedlineCitation")
        if medline is None:
            return ProviderRecord()

        article_node = medline.find("./Article")
        if article_node is None:
            return ProviderRecord()

        pmid = medline.findtext("./PMID", default="").strip()

        doi = ""
        for node in article_node.findall("./ELocationID"):
            if node.get("EIdType", "").lower() == "doi" and node.text:
                doi = node.text.strip()
                break
        if not doi:
            return ProviderRecord()

        abstract_parts: list[str] = []
        for abs_node in article_node.findall("./Abstract/AbstractText"):
            text = (abs_node.text or "").strip()
            if text:
                abstract_parts.append(text)

        authors: list[str] = []
        affiliations: list[str] = []
        for author in article_node.findall("./AuthorList/Author"):
            last = author.findtext("LastName", default="").strip()
            fore = author.findtext("ForeName", default="").strip()
            collective = author.findtext("CollectiveName", default="").strip()
            if last or fore:
                authors.append(" ".join(part for part in (fore, last) if part).strip())
            elif collective:
                authors.append(collective)

            for aff in author.findall("./AffiliationInfo/Affiliation"):
                text = (aff.text or "").strip()
                if text:
                    affiliations.append(text)

        keywords: list[str] = []
        for node in article_node.findall("./KeywordList/Keyword"):
            text = (node.text or "").strip()
            if text:
                keywords.append(text)

        for mesh in medline.findall("./MeshHeadingList/MeshHeading"):
            descriptor = mesh.findtext("./DescriptorName", default="").strip()
            qualifier = mesh.findtext("./QualifierName", default="").strip()
            if descriptor and qualifier:
                keywords.append(f"{descriptor} ({qualifier})")
            elif descriptor:
                keywords.append(descriptor)

        pub_date = article_node.find("./Journal/JournalIssue/PubDate")
        date_text = ""
        if pub_date is not None:
            year = pub_date.findtext("Year", default="").strip()
            month = pub_date.findtext("Month", default="").strip()
            day = pub_date.findtext("Day", default="").strip()
            date_text = "-".join(part for part in (year, month, day) if part)

        return ProviderRecord(
            doi=doi,
            title=article_node.findtext("./ArticleTitle", default="").strip(),
            keywords=keywords,
            abstract="\n".join(abstract_parts),
            journal=article_node.findtext("./Journal/Title", default="").strip(),
            corresponding_author=authors[0] if authors else "",
            affiliations=affiliations,
            source=self.key,
            publisher=article_node.findtext("./Journal/PublisherName", default="").strip(),
            published_date=date_text,
            url=f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/" if pmid else "",
        )

    def search(self, query: ProviderQuery, max_results: int) -> list[ProviderRecord]:
        ids = self._esearch(query=query.compiled_query, retmax=max_results)
        if not ids:
            return []

        batch_size = 100
        records: list[ProviderRecord] = []
        for idx in range(0, len(ids), batch_size):
            chunk = ids[idx : idx + batch_size]
            records.extend(self._efetch(chunk))
            if len(records) >= max_results:
                break
            self._sleep()

        return records[:max_results]
