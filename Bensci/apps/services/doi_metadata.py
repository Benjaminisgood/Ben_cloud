from __future__ import annotations

import re
from urllib.parse import quote

import requests

from apps.core.config import settings


def _clean_html(text: str) -> str:
    if not text:
        return ""
    return re.sub(r"<[^>]+>", "", text).strip()


def _pick_date(item: dict) -> str:
    for key in ("published-print", "published-online", "issued", "created"):
        value = item.get(key) or {}
        parts = value.get("date-parts") or []
        if parts and isinstance(parts[0], list):
            return "-".join(str(piece) for piece in parts[0])
    return ""


def _extract_crossref(doi: str) -> dict[str, object]:
    url = f"https://api.crossref.org/works/{quote(doi, safe='')}"
    response = requests.get(
        url,
        timeout=settings.request_timeout_seconds,
        headers={"User-Agent": settings.request_user_agent},
    )
    if response.status_code != 200:
        return {}

    payload = response.json()
    item = (payload.get("message") or {}) if isinstance(payload, dict) else {}
    if not item:
        return {}

    title_values = item.get("title") or []
    title = str(title_values[0]).strip() if title_values else ""
    container = item.get("container-title") or []
    journal = str(container[0]).strip() if container else ""

    keywords = [str(value).strip() for value in (item.get("subject") or []) if str(value).strip()]

    authors: list[str] = []
    affiliations: list[str] = []
    corresponding_author = ""
    for author in item.get("author") or []:
        given = str(author.get("given") or "").strip()
        family = str(author.get("family") or "").strip()
        full_name = " ".join(piece for piece in (given, family) if piece).strip()
        if not full_name:
            full_name = str(author.get("name") or "").strip()
        if full_name:
            authors.append(full_name)
        if not corresponding_author and author.get("sequence") == "first" and full_name:
            corresponding_author = full_name

        for aff in author.get("affiliation") or []:
            name = str((aff or {}).get("name") or "").strip()
            if name:
                affiliations.append(name)

    if not corresponding_author and authors:
        corresponding_author = authors[0]

    return {
        "title": title,
        "keywords": keywords,
        "abstract": _clean_html(str(item.get("abstract") or "")),
        "journal": journal,
        "corresponding_author": corresponding_author,
        "affiliations": affiliations,
        "publisher": str(item.get("publisher") or "").strip(),
        "published_date": _pick_date(item),
        "url": str(item.get("URL") or "").strip(),
    }


def _extract_openalex(doi: str) -> dict[str, object]:
    encoded = quote(f"https://doi.org/{doi}", safe="")
    url = f"https://api.openalex.org/works/{encoded}"
    response = requests.get(
        url,
        timeout=settings.request_timeout_seconds,
        headers={"User-Agent": settings.request_user_agent},
    )
    if response.status_code != 200:
        return {}

    item = response.json() if response.text else {}
    if not isinstance(item, dict) or not item:
        return {}

    host = item.get("host_venue") or {}
    primary = item.get("primary_location") or {}
    source = primary.get("source") or {}

    authorships = item.get("authorships") or []
    corresponding_author = ""
    affiliations: list[str] = []
    for authorship in authorships:
        author = authorship.get("author") or {}
        name = str(author.get("display_name") or "").strip()
        if authorship.get("is_corresponding") and name and not corresponding_author:
            corresponding_author = name
        for inst in authorship.get("institutions") or []:
            inst_name = str((inst or {}).get("display_name") or "").strip()
            if inst_name:
                affiliations.append(inst_name)

    if not corresponding_author and authorships:
        corresponding_author = str(((authorships[0] or {}).get("author") or {}).get("display_name") or "").strip()

    concepts = [
        str((concept or {}).get("display_name") or "").strip()
        for concept in item.get("concepts") or []
        if (concept or {}).get("display_name")
    ]

    journal = str(host.get("display_name") or "").strip()
    return {
        "title": str(item.get("title") or "").strip(),
        "keywords": concepts,
        "abstract": "",
        "journal": journal,
        "corresponding_author": corresponding_author,
        "affiliations": affiliations,
        "publisher": str(host.get("publisher") or "").strip(),
        "published_date": str(item.get("publication_date") or item.get("publication_year") or "").strip(),
        "url": str(primary.get("landing_page_url") or source.get("host_page_url") or item.get("id") or "").strip(),
    }


def fetch_metadata_by_doi(doi: str) -> dict[str, object]:
    doi = (doi or "").strip().lower()
    if not doi:
        return {}

    merged: dict[str, object] = {}
    for source in (_extract_crossref(doi), _extract_openalex(doi)):
        for key, value in source.items():
            if value in (None, "", [], 0):
                continue
            if key == "keywords":
                existing = merged.get("keywords") or []
                merged_keywords = []
                seen = set()
                for item in list(existing) + list(value):
                    text = str(item).strip()
                    if not text:
                        continue
                    k = text.lower()
                    if k in seen:
                        continue
                    seen.add(k)
                    merged_keywords.append(text)
                merged["keywords"] = merged_keywords
                continue
            if key == "affiliations":
                existing = merged.get("affiliations") or []
                merged_aff = []
                seen = set()
                for item in list(existing) + list(value):
                    text = str(item).strip()
                    if not text:
                        continue
                    k = text.lower()
                    if k in seen:
                        continue
                    seen.add(k)
                    merged_aff.append(text)
                merged["affiliations"] = merged_aff
                continue
            if key == "abstract":
                current = str(merged.get("abstract") or "")
                candidate = str(value or "")
                if len(candidate) > len(current):
                    merged[key] = candidate
                continue
            if key not in merged:
                merged[key] = value

    return merged
