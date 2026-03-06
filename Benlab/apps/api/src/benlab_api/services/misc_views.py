from __future__ import annotations

import csv
import io
import json
from typing import Any

from fastapi import Request
from fastapi.responses import Response

from benlab_api.core.constants import ITEM_STATUS_CHOICES, LOCATION_STATUS_CHOICES
from benlab_api.models import Event, Item, Location, Log, Member, Message


def build_graph_json(
    current_user: Member,
    *,
    members: list[Member],
    items: list[Item],
    locations: list[Location],
    events: list[Event],
) -> str:
    nodes: list[dict[str, Any]] = []
    links: list[dict[str, Any]] = []

    def add_node(node_id: str, label: str, node_type: str, meta: dict[str, Any] | None = None) -> None:
        nodes.append({"id": node_id, "label": label, "type": node_type, "meta": meta or {}})

    center_id = f"member:{current_user.id}"
    add_node(
        center_id,
        current_user.name or current_user.username,
        "member",
        {"isCenter": True, "username": current_user.username, "relation": "self"},
    )

    for member in members:
        node_id = f"member:{member.id}"
        add_node(node_id, member.name or member.username, "member", {"username": member.username})
        links.append({"source": center_id, "target": node_id, "kind": "social"})

    for item in items:
        node_id = f"item:{item.id}"
        add_node(node_id, item.name, "item", {"category": item.category, "status": item.status})
        links.append({"source": center_id, "target": node_id, "kind": "responsible-item"})

    for location in locations:
        node_id = f"location:{location.id}"
        add_node(node_id, location.name, "location", {"status": location.status})
        links.append({"source": center_id, "target": node_id, "kind": "responsible-location"})

    for event in events:
        node_id = f"event:{event.id}"
        start_text = event.start_time.strftime("%Y-%m-%d %H:%M") if event.start_time else ""
        add_node(node_id, event.title, "event", {"startTime": start_text, "visibility": event.visibility})
        links.append({"source": center_id, "target": node_id, "kind": "event"})

    return json.dumps({"nodes": nodes, "links": links}, ensure_ascii=False)


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
