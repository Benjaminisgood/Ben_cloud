from __future__ import annotations

from typing import Any

from benlab_api.models import MemberConnection


MEMBER_CONNECTION_TYPES = {
    "family": "家人",
    "partner": "伴侣",
    "friend": "朋友",
    "close_friend": "密友",
    "classmate": "同学",
    "colleague": "同事",
    "mentor": "导师",
    "mentee": "学生",
    "collaborator": "合作伙伴",
    "client": "客户",
    "neighbor": "邻居",
    "other": "其他",
}

MEMBER_CONNECTION_CLOSENESS = {
    1: "点头之交",
    2: "认识",
    3: "熟悉",
    4: "亲近",
    5: "核心关系",
}


def _ensure_string(value: object | None) -> str:
    if value is None:
        return ""
    return str(value)


def normalize_connection_type(value: object | None) -> str:
    token = _ensure_string(value).strip()
    if token in MEMBER_CONNECTION_TYPES:
        return token
    return "other"


def normalize_closeness(value: object | None) -> int | None:
    token = _ensure_string(value).strip()
    if not token:
        return None
    try:
        level = int(token)
    except (TypeError, ValueError):
        return None
    return level if level in MEMBER_CONNECTION_CLOSENESS else None


def parse_member_connections_form(form: Any, *, source_member_id: int) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    seen_targets: set[int] = set()
    for target_id_raw, relation_raw, closeness_raw, note_raw in zip(
        form.getlist("connection_target_id"),
        form.getlist("connection_relation_type"),
        form.getlist("connection_closeness"),
        form.getlist("connection_note"),
    ):
        try:
            target_id = int(target_id_raw)
        except (TypeError, ValueError):
            continue
        if target_id == source_member_id or target_id in seen_targets:
            continue
        seen_targets.add(target_id)
        rows.append(
            {
                "target_member_id": target_id,
                "relation_type": normalize_connection_type(relation_raw),
                "closeness": normalize_closeness(closeness_raw),
                "note": _ensure_string(note_raw).strip(),
            }
        )
    return rows


def apply_member_connections(
    existing_connections: list[MemberConnection],
    submitted_connections: list[dict[str, object]],
    *,
    valid_target_ids: set[int],
) -> tuple[list[MemberConnection], list[MemberConnection]]:
    existing_by_target = {connection.target_member_id: connection for connection in existing_connections}
    keep_target_ids = {
        int(entry["target_member_id"])
        for entry in submitted_connections
        if int(entry["target_member_id"]) in valid_target_ids
    }
    to_delete = [connection for connection in existing_connections if connection.target_member_id not in keep_target_ids]

    to_upsert: list[MemberConnection] = []
    for entry in submitted_connections:
        target_member_id = int(entry["target_member_id"])
        if target_member_id not in valid_target_ids:
            continue
        connection = existing_by_target.get(target_member_id)
        if connection is None:
            connection = MemberConnection(target_member_id=target_member_id)
        connection.relation_type = normalize_connection_type(entry.get("relation_type"))
        connection.closeness = normalize_closeness(entry.get("closeness"))
        connection.note = _ensure_string(entry.get("note")).strip()
        to_upsert.append(connection)
    return to_upsert, to_delete


def build_member_connection_view(connections: list[MemberConnection]) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for connection in connections:
        if connection.target_member is None:
            continue
        rows.append(
            {
                "connection": connection,
                "target_member": connection.target_member,
                "relation_label": MEMBER_CONNECTION_TYPES.get(connection.relation_type, MEMBER_CONNECTION_TYPES["other"]),
                "closeness_label": MEMBER_CONNECTION_CLOSENESS.get(connection.closeness or 0, ""),
                "note": _ensure_string(connection.note).strip(),
            }
        )
    return rows
