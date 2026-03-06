from __future__ import annotations

import re


def normalize_doi(doi: str) -> str:
    value = (doi or "").strip()
    if not value:
        return ""
    value = re.sub(r"^https?://(dx\.)?doi\.org/", "", value, flags=re.IGNORECASE)
    value = re.sub(r"^doi:\s*", "", value, flags=re.IGNORECASE)
    return value.strip().lower()


def normalize_list(items: list[str] | None) -> list[str]:
    if not items:
        return []
    seen: set[str] = set()
    output: list[str] = []
    for raw in items:
        text = str(raw).strip()
        if not text:
            continue
        key = text.lower()
        if key in seen:
            continue
        seen.add(key)
        output.append(text)
    return output


def split_semicolon(value: str) -> list[str]:
    if not value:
        return []
    return normalize_list([item.strip() for item in value.split(";") if item.strip()])


def join_semicolon(items: list[str] | None) -> str:
    return "; ".join(normalize_list(items))
