from __future__ import annotations

from datetime import date, datetime
from typing import Any


def parse_purchase_date(raw: str | None) -> date | None:
    if not raw:
        return None
    try:
        return datetime.strptime(raw, "%Y-%m-%d").date()
    except ValueError:
        return None


def parse_item_value(raw: str | None) -> float | None:
    token = (raw or "").strip()
    if not token:
        return None
    try:
        return float(token)
    except ValueError:
        return None


def collect_item_detail_refs(form: Any) -> list[dict[str, str]]:
    labels = [str(value).strip() for value in form.getlist("detail_ref_label")]
    values = [str(value).strip() for value in form.getlist("detail_ref_value")]
    output: list[dict[str, str]] = []
    for idx, value in enumerate(values):
        label = labels[idx] if idx < len(labels) else ""
        if label or value:
            output.append({"label": label, "value": value})
    return output


def resolve_item_features(form: Any) -> str:
    explicit = str(form.get("features", "")).strip()
    if explicit:
        return explicit
    return "公共" if form.get("is_public_feature") else "私人"


def parse_external_attachment_refs(raw: str | None) -> list[str]:
    refs: list[str] = []
    seen: set[str] = set()
    for line in (raw or "").splitlines():
        token = line.strip()
        if not token or token in seen:
            continue
        seen.add(token)
        refs.append(token)
    return refs


def sorted_non_empty_categories(items: list[Any]) -> list[str]:
    return sorted({(getattr(item, "category", "") or "").strip() for item in items if (getattr(item, "category", "") or "").strip()})


def build_category_payload(items: list[Any]) -> tuple[list[str], list[dict[str, object]]]:
    grouped: dict[str, list[dict[str, object]]] = {}
    for item in items:
        category = (getattr(item, "category", "") or "").strip()
        if not category:
            continue
        grouped.setdefault(category, []).append({"id": getattr(item, "id"), "name": getattr(item, "name", "")})

    categories = sorted(grouped.keys())
    payload = [{"name": category, "items": grouped[category]} for category in categories]
    return categories, payload
