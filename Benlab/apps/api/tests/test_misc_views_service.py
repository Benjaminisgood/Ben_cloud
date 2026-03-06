from __future__ import annotations

import json
from datetime import datetime
from types import SimpleNamespace

from benlab_api.services.misc_views import (
    build_disabled_autofill_suggestion,
    build_graph_json,
    build_item_search_payload,
    build_location_search_payload,
    to_items_export_rows,
)


def test_build_disabled_autofill_suggestion() -> None:
    assert build_disabled_autofill_suggestion("item") is not None
    assert build_disabled_autofill_suggestion("location") is not None
    assert build_disabled_autofill_suggestion("unknown") is None


def test_build_graph_json() -> None:
    current_user = SimpleNamespace(id=1, name="", username="alice")
    members = [SimpleNamespace(id=2, name="Bob", username="bob")]
    items = [SimpleNamespace(id=10, name="Camera", category="设备", status="正常")]
    locations = [SimpleNamespace(id=20, name="Lab", status="正常")]
    events = [SimpleNamespace(id=30, title="Demo", start_time=datetime(2026, 2, 27, 12, 0), visibility="public")]

    graph = json.loads(
        build_graph_json(
            current_user,
            members=members,
            items=items,
            locations=locations,
            events=events,
        )
    )
    assert len(graph["nodes"]) == 5
    assert len(graph["links"]) == 4


def test_search_payload_builders() -> None:
    class _DummyRequest:
        @staticmethod
        def url_for(name: str, **params):
            if name == "item_detail":
                return f"http://testserver/items/{params['item_id']}"
            if name == "view_location":
                return f"http://testserver/locations/{params['loc_id']}"
            raise KeyError(name)

    request = _DummyRequest()
    item_payload = build_item_search_payload(
        [SimpleNamespace(id=1, name="Camera", category="设备", status="正常")],
        request,  # type: ignore[arg-type]
    )
    location_payload = build_location_search_payload(
        [SimpleNamespace(id=2, name="Lab", status="正常", latitude=1.0, longitude=2.0)],
        request,  # type: ignore[arg-type]
    )

    assert item_payload[0]["detailUrl"].endswith("/items/1")
    assert location_payload[0]["detailUrl"].endswith("/locations/2")


def test_items_export_rows() -> None:
    items = [
        SimpleNamespace(
            id=1,
            name="Camera",
            category="设备",
            status="正常",
            features="公共",
            quantity_desc="1",
            responsible_members=[SimpleNamespace(username="alice")],
            locations=[SimpleNamespace(name="Lab")],
            last_modified=datetime(2026, 2, 27, 11, 0),
        )
    ]
    rows = to_items_export_rows(items)
    assert rows[0]["responsible_members"] == "alice"
    assert rows[0]["locations"] == "Lab"
