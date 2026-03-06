from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from benlab_api.utils.runtime_settings import admin_settings_payload


def format_admin_settings(payload: Mapping[str, Any]) -> dict:
    groups_out: list[dict] = []
    for group in payload.get("groups", []):
        items_out: list[dict] = []
        for setting in group.get("items", []):
            default_value = str(setting.get("default", ""))
            current_value = setting["current_value"]
            source = "default" if str(current_value) == default_value else "override"
            item = {
                "key": setting["key"],
                "label": setting["label"],
                "description": setting["description"],
                "value": current_value,
                "default": default_value,
                "source": source,
                "type": setting["type"],
            }
            if setting.get("min") is not None:
                item["min"] = setting["min"]
            if setting.get("max") is not None:
                item["max"] = setting["max"]
            if setting.get("choices"):
                item["options"] = [{"value": choice, "label": choice} for choice in setting["choices"]]
            items_out.append(item)
        groups_out.append({"name": group["name"], "items": items_out})
    return {"groups": groups_out}


def admin_settings_response() -> dict:
    return format_admin_settings(admin_settings_payload())
