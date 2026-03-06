from __future__ import annotations

from typing import Iterable


def parse_id_list(values: Iterable[str] | str | None) -> list[int]:
    if values is None:
        return []
    raw: list[str]
    if isinstance(values, str):
        raw = [values]
    else:
        raw = list(values)
    ids: list[int] = []
    seen: set[int] = set()
    for value in raw:
        token = str(value).strip()
        if not token:
            continue
        try:
            parsed = int(token)
        except ValueError:
            continue
        if parsed in seen:
            continue
        seen.add(parsed)
        ids.append(parsed)
    return ids


def parse_tags(values: Iterable[str] | str | None) -> list[str]:
    if values is None:
        return []
    if isinstance(values, str):
        values = [v.strip() for v in values.split(",")]
    out: list[str] = []
    seen: set[str] = set()
    for value in values:
        token = str(value).strip()
        if not token or token in seen:
            continue
        seen.add(token)
        out.append(token)
    return out
