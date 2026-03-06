from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from ..utils.runtime_settings import admin_settings_payload


def _to_bool(value: Any) -> bool:
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def format_admin_settings(payload: Mapping[str, Any]) -> dict:
    groups_out: list[dict] = []
    for group in payload.get("groups", []):
        items_out: list[dict] = []
        for setting in group.get("items", []):
            value_type = setting.get("type", "string")
            default_raw = setting.get("default", "")
            current_raw = setting.get("current_value", "")
            if value_type == "bool":
                default_value = _to_bool(default_raw)
                current_value = _to_bool(current_raw)
            else:
                default_value = str(default_raw)
                current_value = str(current_raw)
            source = str(setting.get("source") or "").strip().lower() or (
                "default" if str(current_value) == str(default_value) else "override"
            )
            item = {
                "key": setting["key"],
                "label": setting["label"],
                "description": setting["description"],
                "value": current_value,
                "default": default_value,
                "source": source,
                "type": value_type,
            }
            if setting.get("min") is not None:
                item["min"] = setting["min"]
            if setting.get("max") is not None:
                item["max"] = setting["max"]
            if setting.get("choices"):
                item["options"] = [{"value": choice, "label": choice} for choice in setting["choices"]]
            if setting.get("secret"):
                item["secret"] = True
            items_out.append(item)
        groups_out.append({"name": group["name"], "items": items_out})
    return {"groups": groups_out}


def admin_settings_response() -> dict:
    return format_admin_settings(admin_settings_payload())
