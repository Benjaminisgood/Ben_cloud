from __future__ import annotations

import json
from typing import Iterable


def parse_detail_refs(raw: str | None) -> list[dict[str, str]]:
    text = (raw or "").strip()
    if not text:
        return []
    # JSON array format
    if text.startswith("["):
        try:
            payload = json.loads(text)
        except json.JSONDecodeError:
            payload = None
        if isinstance(payload, list):
            out: list[dict[str, str]] = []
            for entry in payload:
                if isinstance(entry, dict):
                    label = str(entry.get("label", "")).strip()
                    value = str(entry.get("value", "")).strip()
                    if label or value:
                        out.append({"label": label, "value": value})
            if out:
                return out

    # line-by-line fallback: "label:value" or plain value
    out: list[dict[str, str]] = []
    for line in text.splitlines():
        token = line.strip()
        if not token:
            continue
        if token.lower().startswith("usage_tags:"):
            continue
        if ":" in token:
            label, value = token.split(":", 1)
            label = label.strip()
            value = value.strip()
            if label or value:
                out.append({"label": label, "value": value})
        else:
            out.append({"label": "", "value": token})
    return out


def serialize_detail_refs(entries: Iterable[dict[str, str]] | str | None) -> str:
    if entries is None:
        return ""
    if isinstance(entries, str):
        return entries.strip()
    cleaned: list[dict[str, str]] = []
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        label = str(entry.get("label", "")).strip()
        value = str(entry.get("value", "")).strip()
        if not label and not value:
            continue
        cleaned.append({"label": label, "value": value})
    if not cleaned:
        return ""
    return json.dumps(cleaned, ensure_ascii=False)


def parse_usage_tags(raw: str | None) -> list[str]:
    text = (raw or "")
    for line in text.splitlines():
        token = line.strip()
        if token.lower().startswith("usage_tags:"):
            payload = token.split(":", 1)[1]
            out: list[str] = []
            seen: set[str] = set()
            for part in payload.split(","):
                tag = part.strip()
                if not tag or tag in seen:
                    continue
                seen.add(tag)
                out.append(tag)
            return out
    return []
