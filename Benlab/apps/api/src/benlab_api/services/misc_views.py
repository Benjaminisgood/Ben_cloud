from __future__ import annotations

import csv
import io
import json
from typing import Any

from fastapi import Request
from fastapi.responses import Response

from benlab_api.core.constants import ITEM_STATUS_CHOICES, LOCATION_STATUS_CHOICES
from benlab_api.models import Event, Item, Location, Log, Member, Message
from benlab_api.services.admin_identity import is_admin_member
from benlab_api.services.member_connections import MEMBER_CONNECTION_CLOSENESS, MEMBER_CONNECTION_TYPES


GRAPH_LEGEND = {
    "member": "成员",
    "item": "物品",
    "event": "活动",
    "location": "地点",
    "category": "类别",
}

GRAPH_LINK_LABELS = {
    "social": "人物",
    "follow": "关注",
    "member-connection": "人物关系",
    "member-item": "人物-物品",
    "member-location": "人物-空间",
    "location-hierarchy": "空间层级",
    "item-location": "物品-空间",
    "item-category": "物品类别",
    "event-member": "活动参与",
    "event-location": "活动地点",
    "event-item": "活动物品",
}


def _member_node_id(member_id: int) -> str:
    return f"member:{member_id}"


def _item_node_id(item_id: int) -> str:
    return f"item:{item_id}"


def _location_node_id(location_id: int) -> str:
    return f"location:{location_id}"


def _event_node_id(event_id: int) -> str:
    return f"event:{event_id}"


def _category_node_id(category: str) -> str:
    return f"category:{category}"


def _new_graph_payload(mode: str) -> dict[str, Any]:
    return {"mode": mode, "nodes": [], "links": []}


def _add_node(payload: dict[str, Any], node_id: str, label: str, node_type: str, meta: dict[str, Any] | None = None) -> None:
    seen = payload.setdefault("_seen_nodes", set())
    if node_id in seen:
        return
    seen.add(node_id)
    payload["nodes"].append({"id": node_id, "label": label, "type": node_type, "meta": meta or {}})


def _add_link(
    payload: dict[str, Any],
    source: str,
    target: str,
    kind: str,
    *,
    label: str | None = None,
    meta: dict[str, Any] | None = None,
) -> None:
    seen = payload.setdefault("_seen_links", set())
    key = (source, target, kind, label or "")
    if key in seen:
        return
    seen.add(key)
    payload["links"].append(
        {
            "source": source,
            "target": target,
            "kind": kind,
            "label": label or GRAPH_LINK_LABELS.get(kind, kind),
            "meta": meta or {},
        }
    )


def _finalize_graph_payload(payload: dict[str, Any]) -> dict[str, Any]:
    payload.pop("_seen_nodes", None)
    payload.pop("_seen_links", None)
    node_types = sorted({node["type"] for node in payload["nodes"]})
    link_kinds = sorted({link["kind"] for link in payload["links"]})
    payload["nodeLegend"] = {key: value for key, value in GRAPH_LEGEND.items() if key in node_types}
    payload["linkLegend"] = {key: GRAPH_LINK_LABELS.get(key, key) for key in link_kinds}
    return payload


def build_simple_graph_payload(
    current_user: Member,
    *,
    members: list[Member],
    items: list[Item],
    locations: list[Location],
    events: list[Event],
) -> dict[str, Any]:
    payload = _new_graph_payload("simple")
    center_id = _member_node_id(current_user.id)
    _add_node(
        payload,
        center_id,
        current_user.name or current_user.username,
        "member",
        {"isCenter": True, "username": current_user.username, "relation": "self"},
    )

    for member in members:
        node_id = _member_node_id(member.id)
        _add_node(payload, node_id, member.name or member.username, "member", {"username": member.username})
        _add_link(payload, center_id, node_id, "social")

    for item in items:
        node_id = _item_node_id(item.id)
        _add_node(payload, node_id, item.name, "item", {"category": item.category, "status": item.status})
        _add_link(payload, center_id, node_id, "member-item")

    for location in locations:
        node_id = _location_node_id(location.id)
        _add_node(payload, node_id, location.name, "location", {"status": location.status})
        _add_link(payload, center_id, node_id, "member-location")

    for event in events:
        node_id = _event_node_id(event.id)
        start_text = event.start_time.strftime("%Y-%m-%d %H:%M") if event.start_time else ""
        _add_node(payload, node_id, event.title, "event", {"startTime": start_text, "visibility": event.visibility})
        _add_link(payload, center_id, node_id, "event-member")

    return _finalize_graph_payload(payload)


def build_complex_graph_payload(
    current_user: Member,
    *,
    center_member: Member,
    members: list[Member],
    items: list[Item],
    locations: list[Location],
    events: list[Event],
) -> dict[str, Any]:
    payload = _new_graph_payload("complex")
    is_admin = is_admin_member(current_user)
    member_index: dict[int, Member] = {center_member.id: center_member}
    location_index: dict[int, Location] = {}
    item_index: dict[int, Item] = {}
    event_index: dict[int, Event] = {}

    def register_member(member: Member | None) -> None:
        if member is None or member.id in member_index:
            return
        member_index[member.id] = member

    def register_location(location: Location | None) -> None:
        if location is None or location.id in location_index:
            return
        location_index[location.id] = location

    def register_item(item: Item | None) -> None:
        if item is None or item.id in item_index:
            return
        item_index[item.id] = item

    def register_event(event: Event | None) -> None:
        if event is None or event.id in event_index:
            return
        event_index[event.id] = event

    for member in members:
        register_member(member)
        for connection in getattr(member, "outbound_connections", []) or []:
            register_member(getattr(connection, "target_member", None))
        for location in getattr(member, "responsible_locations", []) or []:
            register_location(location)
        for item in getattr(member, "items", []) or []:
            register_item(item)

    for connection in getattr(center_member, "outbound_connections", []) or []:
        register_member(getattr(connection, "target_member", None))
    for follow_member in getattr(center_member, "following", []) or []:
        register_member(follow_member)
    for location in locations:
        register_location(location)
        register_location(getattr(location, "parent", None))
        for child in getattr(location, "children", []) or []:
            register_location(child)
        for member in getattr(location, "responsible_members", []) or []:
            register_member(member)
        for item in getattr(location, "items", []) or []:
            register_item(item)
    for item in items:
        register_item(item)
        for member in getattr(item, "responsible_members", []) or []:
            register_member(member)
        for location in getattr(item, "locations", []) or []:
            register_location(location)
    for event in events:
        register_event(event)
        register_member(getattr(event, "owner", None))
        for link in getattr(event, "participant_links", []) or []:
            register_member(getattr(link, "member", None))
        for item in getattr(event, "items", []) or []:
            register_item(item)
        for location in getattr(event, "locations", []) or []:
            register_location(location)
            register_location(getattr(location, "parent", None))

    center_id = _member_node_id(center_member.id)
    for member in member_index.values():
        _add_node(
            payload,
            _member_node_id(member.id),
            member.name or member.username,
            "member",
            {
                "isCenter": member.id == center_member.id,
                "username": member.username,
                "isAdminOnly": is_admin and any(connection.source_member_id == center_member.id for connection in getattr(center_member, "outbound_connections", []) or []),
            },
        )
    for location in location_index.values():
        _add_node(
            payload,
            _location_node_id(location.id),
            location.name,
            "location",
            {"status": location.status, "parentId": location.parent_id},
        )
    for item in item_index.values():
        _add_node(
            payload,
            _item_node_id(item.id),
            item.name,
            "item",
            {"category": item.category, "status": item.status},
        )
        category = (item.category or "").strip()
        if category:
            _add_node(payload, _category_node_id(category), category, "category", {"category": category})
            _add_link(payload, _item_node_id(item.id), _category_node_id(category), "item-category")
    for event in event_index.values():
        _add_node(
            payload,
            _event_node_id(event.id),
            event.title,
            "event",
            {
                "visibility": event.visibility,
                "startTime": event.start_time.strftime("%Y-%m-%d %H:%M") if event.start_time else "",
            },
        )

    for member in member_index.values():
        member_node_id = _member_node_id(member.id)
        if member.id != center_member.id and member.id in {followed.id for followed in getattr(center_member, "following", []) or []}:
            _add_link(payload, center_id, member_node_id, "follow")
        for location in getattr(member, "responsible_locations", []) or []:
            if location.id in location_index:
                _add_link(payload, member_node_id, _location_node_id(location.id), "member-location")
        for item in getattr(member, "items", []) or []:
            if item.id in item_index:
                _add_link(payload, member_node_id, _item_node_id(item.id), "member-item")
        if is_admin:
            for connection in getattr(member, "outbound_connections", []) or []:
                target_member = getattr(connection, "target_member", None)
                if target_member is None or target_member.id not in member_index:
                    continue
                relation_label = MEMBER_CONNECTION_TYPES.get(connection.relation_type, MEMBER_CONNECTION_TYPES["other"])
                closeness_label = MEMBER_CONNECTION_CLOSENESS.get(connection.closeness or 0, "")
                edge_label = relation_label if not closeness_label else f"{relation_label} / {closeness_label}"
                _add_link(
                    payload,
                    member_node_id,
                    _member_node_id(target_member.id),
                    "member-connection",
                    label=edge_label,
                    meta={"note": connection.note or "", "relationType": connection.relation_type},
                )

    for location in location_index.values():
        if getattr(location, "parent", None) and location.parent.id in location_index:
            _add_link(payload, _location_node_id(location.parent.id), _location_node_id(location.id), "location-hierarchy")
        for member in getattr(location, "responsible_members", []) or []:
            if member.id in member_index:
                _add_link(payload, _member_node_id(member.id), _location_node_id(location.id), "member-location")
        for item in getattr(location, "items", []) or []:
            if item.id in item_index:
                _add_link(payload, _item_node_id(item.id), _location_node_id(location.id), "item-location")

    for item in item_index.values():
        for location in getattr(item, "locations", []) or []:
            if location.id in location_index:
                _add_link(payload, _item_node_id(item.id), _location_node_id(location.id), "item-location")
        for member in getattr(item, "responsible_members", []) or []:
            if member.id in member_index:
                _add_link(payload, _member_node_id(member.id), _item_node_id(item.id), "member-item")

    for event in event_index.values():
        event_id = _event_node_id(event.id)
        owner = getattr(event, "owner", None)
        if owner is not None and owner.id in member_index:
            _add_link(payload, _member_node_id(owner.id), event_id, "event-member", label="主办")
        for link in getattr(event, "participant_links", []) or []:
            participant = getattr(link, "member", None)
            if participant is None or participant.id not in member_index:
                continue
            _add_link(payload, _member_node_id(participant.id), event_id, "event-member", label=getattr(link, "role", "") or "参与")
        for location in getattr(event, "locations", []) or []:
            if location.id in location_index:
                _add_link(payload, event_id, _location_node_id(location.id), "event-location")
        for item in getattr(event, "items", []) or []:
            if item.id in item_index:
                _add_link(payload, event_id, _item_node_id(item.id), "event-item")

    return _finalize_graph_payload(payload)


def build_graph_json(
    current_user: Member,
    *,
    members: list[Member],
    items: list[Item],
    locations: list[Location],
    events: list[Event],
) -> str:
    return json.dumps(
        build_simple_graph_payload(
            current_user,
            members=members,
            items=items,
            locations=locations,
            events=events,
        ),
        ensure_ascii=False,
    )


def build_item_search_payload(items: list[Item], request: Request) -> list[dict[str, Any]]:
    return [
        {
            "id": item.id,
            "name": item.name,
            "category": item.category,
            "status": item.status,
            "detailUrl": str(request.url_for("item_detail", item_id=item.id)),
        }
        for item in items
    ]


def build_location_search_payload(locations: list[Location], request: Request) -> list[dict[str, Any]]:
    return [
        {
            "id": location.id,
            "name": location.name,
            "status": location.status,
            "latitude": location.latitude,
            "longitude": location.longitude,
            "hasCoordinates": location.latitude is not None and location.longitude is not None,
            "detailUrl": str(request.url_for("view_location", loc_id=location.id)),
        }
        for location in locations
    ]


def build_disabled_autofill_suggestion(form_type: str) -> dict[str, Any] | None:
    token = form_type.strip().lower()
    if token == "item":
        return {
            "name": "",
            "category": "",
            "status": ITEM_STATUS_CHOICES[0],
            "notes": "",
            "detail_refs": [],
            "quantity_desc": "",
            "purchase_link": "",
        }
    if token == "location":
        return {
            "name": "",
            "status": LOCATION_STATUS_CHOICES[0],
            "notes": "",
            "detail_link": "",
            "detail_refs": [],
            "usage_tags": [],
        }
    return None


def export_csv(rows: list[dict[str, Any]], filename: str) -> Response:
    buffer = io.StringIO()
    if rows:
        writer = csv.DictWriter(buffer, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    content = buffer.getvalue().encode("utf-8-sig")
    headers = {"Content-Disposition": f'attachment; filename="{filename}"'}
    return Response(content=content, media_type="text/csv", headers=headers)


def to_items_export_rows(items: list[Item]) -> list[dict[str, Any]]:
    return [
        {
            "id": item.id,
            "name": item.name,
            "category": item.category,
            "status": item.status,
            "features": item.features,
            "quantity_desc": item.quantity_desc,
            "responsible_members": ",".join(member.username for member in item.responsible_members),
            "locations": ",".join(location.name for location in item.locations),
            "updated_at": item.last_modified.isoformat() if item.last_modified else "",
        }
        for item in items
    ]


def to_members_export_rows(members: list[Member]) -> list[dict[str, Any]]:
    return [
        {
            "id": member.id,
            "name": member.name,
            "username": member.username,
            "contact": member.contact,
        }
        for member in members
    ]


def to_locations_export_rows(locations: list[Location]) -> list[dict[str, Any]]:
    return [
        {
            "id": location.id,
            "name": location.name,
            "status": location.status,
            "latitude": location.latitude,
            "longitude": location.longitude,
            "members": ",".join(member.username for member in location.responsible_members),
            "updated_at": location.last_modified.isoformat() if location.last_modified else "",
        }
        for location in locations
    ]


def to_logs_export_rows(logs: list[Log]) -> list[dict[str, Any]]:
    return [
        {
            "id": log.id,
            "timestamp": log.timestamp.isoformat() if log.timestamp else "",
            "user_id": log.user_id,
            "item_id": log.item_id,
            "location_id": log.location_id,
            "event_id": log.event_id,
            "action_type": log.action_type,
            "details": log.details,
        }
        for log in logs
    ]


def to_messages_export_rows(messages: list[Message]) -> list[dict[str, Any]]:
    return [
        {
            "id": message.id,
            "timestamp": message.timestamp.isoformat() if message.timestamp else "",
            "sender_id": message.sender_id,
            "receiver_id": message.receiver_id,
            "content": message.content,
        }
        for message in messages
    ]
