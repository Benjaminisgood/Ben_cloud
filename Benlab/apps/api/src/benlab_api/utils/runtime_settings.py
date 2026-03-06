"""Runtime settings for Benlab (file-backed overrides)."""
from __future__ import annotations

import json
import os
from collections import OrderedDict
from pathlib import Path

from benlab_api.core.config import get_settings

SETTING_DEFINITIONS: list[dict] = [
    {
        "key": "BOARD_DEFAULT_DAYS",
        "label": "Board 默认天数",
        "type": "int",
        "group": "站点",
        "description": "Board 页默认展示最近多少天。",
        "min": 1,
        "max": 366,
        "default": 7,
    },
    {
        "key": "BOARD_TOP_TAGS_DAYS",
        "label": "Board 热门标签统计天数（0=历史全部）",
        "type": "int",
        "group": "站点",
        "description": "热门标签统计窗口；0=从最早记录。",
        "min": 0,
        "max": 36500,
        "default": 30,
    },
    {
        "key": "BOARD_TOP_TAGS_LIMIT",
        "label": "Board 热门标签 TopN",
        "type": "int",
        "group": "站点",
        "description": "热门标签最多展示多少个。",
        "min": 1,
        "max": 100,
        "default": 10,
    },
    {
        "key": "DIGEST_TIMEZONE",
        "label": "Digest 时区",
        "type": "string",
        "group": "站点",
        "description": "日报任务时区，例如 Asia/Shanghai。",
        "default": "Asia/Shanghai",
    },
    {
        "key": "VECTOR_TOP_K",
        "label": "向量搜索 Top-K",
        "type": "int",
        "group": "向量搜索",
        "description": "搜索返回最多多少个结果。",
        "min": 1,
        "max": 50,
        "default": 8,
    },
    {
        "key": "VECTOR_MAX_DOCS",
        "label": "向量索引最大文档数",
        "type": "int",
        "group": "向量搜索",
        "description": "重建索引时的文档上限参数。",
        "min": 100,
        "max": 100000,
        "default": 4000,
    },
    {
        "key": "DIRECT_OSS_UPLOAD_ENABLED",
        "label": "直传上传开关",
        "type": "bool",
        "group": "上传",
        "description": "是否启用 direct-upload 接口。",
        "default": False,
    },
]

_DEFN_MAP = {row["key"]: row for row in SETTING_DEFINITIONS}


def _default_as_str(key: str) -> str:
    if key == "DIRECT_OSS_UPLOAD_ENABLED":
        return "1" if bool(get_settings().DIRECT_OSS_UPLOAD_ENABLED) else "0"
    defn = _DEFN_MAP.get(key)
    if not defn:
        return ""
    raw = defn.get("default", "")
    if isinstance(raw, bool):
        return "1" if raw else "0"
    return str(raw)


def _settings_file() -> Path:
    custom = os.getenv("BENLAB_ADMIN_SETTINGS_FILE", "").strip()
    if custom:
        return Path(custom).expanduser()
    settings = get_settings()
    settings.ensure_data_dirs()
    return settings.DATA_DIR / "admin_settings.json"


def _load_overrides() -> dict[str, str]:
    path = _settings_file()
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}
    if not isinstance(payload, dict):
        return {}

    out: dict[str, str] = {}
    for key, value in payload.items():
        if isinstance(key, str):
            out[key] = str(value)
    return out


def _save_overrides(overrides: dict[str, str]) -> None:
    path = _settings_file()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(overrides, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _coerce_value(defn: dict, raw_value: object) -> str:
    token = str(raw_value).strip()
    value_type = defn.get("type")
    if value_type == "int":
        try:
            parsed = int(token)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"{defn['key']}: expected integer") from exc
        if defn.get("min") is not None and parsed < int(defn["min"]):
            raise ValueError(f"{defn['key']}: must be >= {defn['min']}")
        if defn.get("max") is not None and parsed > int(defn["max"]):
            raise ValueError(f"{defn['key']}: must be <= {defn['max']}")
        return str(parsed)

    if value_type == "bool":
        return "1" if token.lower() in {"1", "true", "yes", "on"} else "0"

    if value_type == "choice":
        choices = [str(v) for v in defn.get("choices") or []]
        if token not in choices:
            raise ValueError(f"{defn['key']}: invalid option")
        return token

    return token


def get_setting_str(key: str, *, default: str = "") -> str:
    overrides = _load_overrides()
    if key in overrides:
        return str(overrides[key])

    env_key = key.upper()
    if env_key in os.environ:
        return str(os.environ[env_key])

    cfg = get_settings()
    if hasattr(cfg, env_key):
        cfg_val = getattr(cfg, env_key)
        if isinstance(cfg_val, bool):
            return "1" if cfg_val else "0"
        return str(cfg_val)

    if key in _DEFN_MAP:
        return _default_as_str(key)
    return default


def get_setting_int(key: str, *, default: int = 0) -> int:
    raw = get_setting_str(key, default=str(default))
    try:
        return int(raw)
    except (TypeError, ValueError):
        return default


def get_setting_bool(key: str, *, default: bool = False) -> bool:
    raw = get_setting_str(key, default="1" if default else "0").strip().lower()
    return raw in {"1", "true", "yes", "on"}


def admin_settings_payload() -> dict:
    overrides = _load_overrides()
    groups: dict[str, list[dict]] = OrderedDict()

    for defn in SETTING_DEFINITIONS:
        key = defn["key"]
        group = str(defn.get("group") or "General")
        item = dict(defn)
        item["current_value"] = overrides.get(key, get_setting_str(key, default=_default_as_str(key)))
        groups.setdefault(group, []).append(item)

    return {"groups": [{"name": group_name, "items": items} for group_name, items in groups.items()]}


def save_admin_settings(values: dict, *, reset_keys: list[str] | None = None) -> dict:
    reset_keys = reset_keys or []
    overrides = _load_overrides()

    for key in reset_keys:
        overrides.pop(str(key), None)

    for key, raw_value in values.items():
        key_str = str(key)
        defn = _DEFN_MAP.get(key_str)
        if not defn:
            raise ValueError(f"unknown setting key: {key_str}")
        overrides[key_str] = _coerce_value(defn, raw_value)

    _save_overrides(overrides)
    return admin_settings_payload()
