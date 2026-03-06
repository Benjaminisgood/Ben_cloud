from __future__ import annotations

from types import SimpleNamespace

from benlab_api.services.location_views import (
    build_affiliation_summary,
    build_location_detail_refs,
    build_location_item_stats,
    collect_location_detail_refs,
    filter_available_items,
    resolve_location_item_ids,
    to_float,
)


class _DummyForm:
    def __init__(self, data: dict[str, object]):
        self._data = data

    def getlist(self, key: str):
        value = self._data.get(key, [])
        if isinstance(value, list):
            return value
        return [value]


def test_to_float() -> None:
    assert to_float("12.5") == 12.5
    assert to_float("abc") is None
    assert to_float(" ") is None


def test_collect_location_detail_refs() -> None:
    form = _DummyForm(
        {
            "detail_ref_label": ["地图", ""],
            "detail_ref_value": ["A-1", "补充"],
        }
    )
    refs = collect_location_detail_refs(form)
    assert refs == [
        {"label": "地图", "value": "A-1"},
        {"label": "", "value": "补充"},
    ]


def test_build_location_detail_refs() -> None:
    entries = [{"label": "地图", "value": "A-1"}]
    detail = build_location_detail_refs("", ["仓储", "公共"], entries)
    assert "地图: A-1" in detail
    assert "usage_tags:仓储,公共" in detail


def test_build_location_item_stats() -> None:
    items = [
        SimpleNamespace(status="正常", category="实验", features="公共"),
        SimpleNamespace(status="维修", category="实验", features="私人"),
        SimpleNamespace(status="", category="", features=""),
    ]
    status_stats, category_stats, feature_stats = build_location_item_stats(items)
    assert {row["label"]: row["count"] for row in status_stats}["正常"] == 2
    assert {row["label"]: row["count"] for row in category_stats}["实验"] == 2
    assert {row["label"]: row["count"] for row in feature_stats}["未标注"] == 1


def test_build_affiliation_summary() -> None:
    members = [SimpleNamespace(name="", username="alice"), SimpleNamespace(name="Bob", username="bob")]
    summary = build_affiliation_summary(members)
    assert [entry["name"] for entry in summary] == ["alice", "Bob"]


def test_resolve_location_item_ids_and_filter_available_items() -> None:
    form = _DummyForm(
        {
            "existing_item_ids": ["1", "2"],
            "remove_item_ids": ["3"],
            "item_ids": ["4", "5"],
        }
    )
    assert resolve_location_item_ids(form, action="add_existing") == [1, 2]
    assert resolve_location_item_ids(form, action="remove") == [3]
    assert resolve_location_item_ids(form, action="add") == [4, 5]

    all_items = [SimpleNamespace(id=1), SimpleNamespace(id=2), SimpleNamespace(id=3)]
    assigned = [SimpleNamespace(id=2)]
    available = filter_available_items(all_items, assigned)
    assert [item.id for item in available] == [1, 3]
