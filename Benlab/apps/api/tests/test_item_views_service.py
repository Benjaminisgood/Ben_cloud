from __future__ import annotations

from types import SimpleNamespace

from benlab_api.services.item_views import (
    build_category_payload,
    collect_item_detail_refs,
    parse_external_attachment_refs,
    parse_item_value,
    parse_purchase_date,
    resolve_item_features,
    sorted_non_empty_categories,
)


class _DummyForm:
    def __init__(self, data: dict[str, object]):
        self._data = data

    def get(self, key: str, default: object = None):
        return self._data.get(key, default)

    def getlist(self, key: str):
        value = self._data.get(key, [])
        if isinstance(value, list):
            return value
        return [value]


def test_parse_purchase_date() -> None:
    assert str(parse_purchase_date("2026-02-27")) == "2026-02-27"
    assert parse_purchase_date("2026/02/27") is None
    assert parse_purchase_date("") is None


def test_parse_item_value() -> None:
    assert parse_item_value("18.5") == 18.5
    assert parse_item_value("not-number") is None
    assert parse_item_value(" ") is None


def test_collect_item_detail_refs() -> None:
    form = _DummyForm(
        {
            "detail_ref_label": ["官网", "说明"],
            "detail_ref_value": ["https://example.com", ""],
        }
    )
    refs = collect_item_detail_refs(form)
    assert refs == [
        {"label": "官网", "value": "https://example.com"},
        {"label": "说明", "value": ""},
    ]


def test_resolve_item_features() -> None:
    assert resolve_item_features(_DummyForm({"features": "专用", "is_public_feature": True})) == "专用"
    assert resolve_item_features(_DummyForm({"is_public_feature": True})) == "公共"
    assert resolve_item_features(_DummyForm({})) == "私人"


def test_parse_external_attachment_refs_deduplicate() -> None:
    refs = parse_external_attachment_refs("https://a\nhttps://b\nhttps://a")
    assert refs == ["https://a", "https://b"]


def test_build_category_payload() -> None:
    items = [
        SimpleNamespace(id=1, name="显微镜", category="实验"),
        SimpleNamespace(id=2, name="白板", category="办公"),
        SimpleNamespace(id=3, name="温度计", category="实验"),
    ]
    categories, payload = build_category_payload(items)
    assert categories == ["办公", "实验"]
    assert payload[1]["items"] == [{"id": 1, "name": "显微镜"}, {"id": 3, "name": "温度计"}]
    assert sorted_non_empty_categories(items) == ["办公", "实验"]
