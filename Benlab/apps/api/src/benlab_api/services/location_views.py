from __future__ import annotations

from typing import Any

from benlab_api.services.forms import parse_id_list


def to_float(raw: str | None) -> float | None:
    if raw is None:
        return None
    token = str(raw).strip()
    if not token:
        return None
    try:
        return float(token)
    except ValueError:
        return None


def collect_location_detail_refs(form: Any) -> list[dict[str, str]]:
    labels = [str(value).strip() for value in form.getlist("detail_ref_label")]
    values = [str(value).strip() for value in form.getlist("detail_ref_value")]
    output: list[dict[str, str]] = []
    for idx, value in enumerate(values):
        label = labels[idx] if idx < len(labels) else ""
        if label or value:
            output.append({"label": label, "value": value})
    return output


def _merge_usage_tags(raw_text: str, usage_tags: list[str]) -> str:
    text = (raw_text or "").strip()
    if usage_tags:
        usage_line = f"usage_tags:{','.join(usage_tags)}"
        text = f"{text}\n{usage_line}" if text else usage_line
    return text


def build_location_detail_refs(raw_text: str, usage_tags: list[str], entries: list[dict[str, str]]) -> str:
    detail_text = (raw_text or "").strip()
    if entries:
        lines: list[str] = []
        for entry in entries:
            label = str(entry.get("label", "")).strip()
            value = str(entry.get("value", "")).strip()
            if not label and not value:
                continue
            lines.append(f"{label}: {value}" if label else value)
        detail_text = "\n".join(lines)
    return _merge_usage_tags(detail_text, usage_tags)


def build_location_item_stats(items: list[Any]) -> tuple[list[dict[str, object]], list[dict[str, object]], list[dict[str, object]]]:
    if not items:
        return [], [], []

    status_counter: dict[str, int] = {}
    category_counter: dict[str, int] = {}
    feature_counter: dict[str, int] = {}
    for item in items:
        status_key = (getattr(item, "status", "") or "正常").strip() or "正常"
        category_key = (getattr(item, "category", "") or "未分类").strip() or "未分类"
        feature_key = (getattr(item, "features", "") or "未标注").strip() or "未标注"

        status_counter[status_key] = status_counter.get(status_key, 0) + 1
        category_counter[category_key] = category_counter.get(category_key, 0) + 1
        feature_counter[feature_key] = feature_counter.get(feature_key, 0) + 1

    status_stats = [{"label": key, "count": value} for key, value in sorted(status_counter.items())]
    category_stats = [{"label": key, "count": value} for key, value in sorted(category_counter.items())]
    feature_stats = [{"label": key, "count": value} for key, value in sorted(feature_counter.items())]
    return status_stats, category_stats, feature_stats


def build_affiliation_summary(members: list[Any]) -> list[dict[str, object]]:
    return [{"name": member.name or member.username, "member": member} for member in members]


def resolve_location_item_ids(form: Any, *, action: str) -> list[int]:
    if action == "add_existing":
        return parse_id_list(form.getlist("existing_item_ids"))
    if action == "remove":
        return parse_id_list(form.getlist("remove_item_ids"))
    return parse_id_list(form.getlist("item_ids"))


def filter_available_items(all_items: list[Any], assigned_items: list[Any]) -> list[Any]:
    assigned_ids = {getattr(item, "id") for item in assigned_items}
    return [item for item in all_items if getattr(item, "id") not in assigned_ids]
