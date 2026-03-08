from __future__ import annotations

import json
from datetime import datetime
from types import SimpleNamespace

from benlab_api.core.config import get_settings
from benlab_api.services.misc_views import (
    build_disabled_autofill_suggestion,
    build_complex_graph_payload,
    build_graph_json,
    build_item_search_payload,
    build_location_search_payload,
    build_simple_graph_payload,
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


def test_build_simple_and_complex_graph_payloads() -> None:
    admin_username = get_settings().ADMIN_USERNAME
    center_user = SimpleNamespace(
        id=1,
        name="Admin",
        username=admin_username,
        following=[],
        outbound_connections=[],
        items=[],
        responsible_locations=[],
    )
    target_member = SimpleNamespace(
        id=2,
        name="Bob",
        username="bob",
        outbound_connections=[],
        following=[],
        responsible_locations=[],
        items=[],
    )
    connection = SimpleNamespace(
        source_member_id=1,
        target_member_id=2,
        relation_type="friend",
        closeness=4,
        note="校友",
        target_member=target_member,
    )
    center_user.outbound_connections = [connection]
    center_user.following = [target_member]

    location = SimpleNamespace(id=20, name="Lab", status="正常", parent_id=None, parent=None, children=[], responsible_members=[center_user, target_member], items=[])
    item = SimpleNamespace(id=10, name="Camera", category="设备", status="正常", locations=[location], responsible_members=[center_user])
    event = SimpleNamespace(
        id=30,
        title="Demo",
        start_time=datetime(2026, 2, 27, 12, 0),
        visibility="public",
        owner=center_user,
        participant_links=[SimpleNamespace(member=target_member, role="guest")],
        items=[item],
        locations=[location],
    )
    center_user.items = [item]
    center_user.responsible_locations = [location]
    target_member.responsible_locations = [location]
    target_member.items = []
    location.items = [item]

    simple = build_simple_graph_payload(center_user, members=[target_member], items=[item], locations=[location], events=[event])
    assert simple["mode"] == "simple"
    assert "member" in simple["nodeLegend"]
    assert len(simple["nodes"]) == 5

    complex_payload = build_complex_graph_payload(
        center_user,
        center_member=center_user,
        members=[target_member],
        items=[item],
        locations=[location],
        events=[event],
    )
    kinds = {link["kind"] for link in complex_payload["links"]}
    node_types = {node["type"] for node in complex_payload["nodes"]}
    assert complex_payload["mode"] == "complex"
    assert "member-connection" in kinds
    assert "member-location" in kinds
    assert "item-category" in kinds
    assert "event-location" in kinds
    assert "category" in node_types


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
