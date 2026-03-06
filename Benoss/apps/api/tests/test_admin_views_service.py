from __future__ import annotations

import sys
from pathlib import Path

API_SRC_DIR = Path(__file__).resolve().parents[1] / "src"
if str(API_SRC_DIR) not in sys.path:
    sys.path.insert(0, str(API_SRC_DIR))

from benoss_api.services.admin_views import admin_settings_response, format_admin_settings
from benoss_api.utils.runtime_settings import SETTING_DEFINITIONS


def _sample_payload() -> dict:
    return {
        "groups": [
            {
                "name": "AI",
                "items": [
                    {
                        "key": "AI_PROVIDER",
                        "label": "Provider",
                        "description": "AI provider",
                        "type": "str",
                        "default": "openai",
                        "current_value": "openai",
                        "choices": ["openai", "dashscope"],
                    },
                    {
                        "key": "TOP_K",
                        "label": "Top K",
                        "description": "Result size",
                        "type": "int",
                        "default": 6,
                        "current_value": "9",
                        "min": 1,
                        "max": 20,
                    },
                ],
            }
        ]
    }


def test_format_admin_settings_maps_fields() -> None:
    out = format_admin_settings(_sample_payload())
    assert out["groups"][0]["name"] == "AI"
    provider = out["groups"][0]["items"][0]
    assert provider["source"] == "default"
    assert provider["options"] == [{"value": "openai", "label": "openai"}, {"value": "dashscope", "label": "dashscope"}]
    top_k = out["groups"][0]["items"][1]
    assert top_k["source"] == "override"
    assert top_k["min"] == 1
    assert top_k["max"] == 20


def test_admin_settings_response_uses_runtime_payload(monkeypatch) -> None:
    from benoss_api.services import admin_views

    monkeypatch.setattr(admin_views, "admin_settings_payload", _sample_payload)
    out = admin_settings_response()
    assert out["groups"][0]["items"][0]["key"] == "AI_PROVIDER"


def test_format_admin_settings_preserves_secret_and_bool() -> None:
    payload = {
        "groups": [
            {
                "name": "providers",
                "items": [
                    {
                        "key": "OPENAI_API_KEY",
                        "label": "OpenAI API Key",
                        "description": "secret",
                        "type": "string",
                        "default": "",
                        "current_value": "abc",
                        "secret": True,
                        "source": "override",
                    },
                    {
                        "key": "ARCHIVE_STORE_FILE_BLOB",
                        "label": "Archive Store Blob",
                        "description": "bool",
                        "type": "bool",
                        "default": True,
                        "current_value": "0",
                        "source": "config",
                    },
                ],
            }
        ]
    }
    out = format_admin_settings(payload)
    secret_item = out["groups"][0]["items"][0]
    assert secret_item["secret"] is True
    assert secret_item["source"] == "override"
    bool_item = out["groups"][0]["items"][1]
    assert bool_item["value"] is False
    assert bool_item["default"] is True
    assert bool_item["source"] == "config"


def test_runtime_setting_definitions_include_extended_admin_keys() -> None:
    keys = {row["key"] for row in SETTING_DEFINITIONS}
    assert "OPENAI_API_KEY" in keys
    assert "OPENAI_CHAT_MODEL" in keys
    assert "CHAT_ANYWHERE_API_KEY" in keys
    assert "DEEPSEEK_API_BASE_URL" in keys
    assert "ALIYUN_AI_API_KEY" in keys
    assert "NOTICE_POSTER_TASK" in keys
    assert "POSTER_SYSTEM_PROMPT" in keys
    assert "POSTER_USER_TEMPLATE" in keys
    assert "AI_ARCHIVE_MULTIMODAL_PARSE" in keys
    assert "AI_NOTICE_FILE_READ_MAX_BYTES" in keys
    assert "VECTOR_EMBEDDING_BATCH_SIZE" in keys
