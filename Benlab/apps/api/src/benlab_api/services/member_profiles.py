from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from benlab_api.models import Event

MEMBER_RELATION_TYPES = {
    "study": "上学",
    "work": "工作",
    "live": "居住",
    "own": "拥有",
    "other": "其他",
}
MEMBER_ITEM_REL_TYPES = {
    "borrow": "租借",
    "praise": "好评",
    "favorite": "收藏",
    "wishlist": "待购",
    "other": "其他",
}
MEMBER_EVENT_REL_TYPES = {
    "host": "主办",
    "join": "参与",
    "support": "协助",
    "follow": "关注",
    "interested": "想参加",
    "other": "其他",
}


def _ensure_string(value: object | None) -> str:
    if value is None:
        return ""
    return str(value)


def _empty_profile_meta() -> dict[str, object]:
    return {
        "bio": "",
        "social_links": [],
        "location_relations": [],
        "item_relations": [],
        "event_relations": [],
    }


def _normalize_relation_entries(
    entries: object,
    *,
    id_key: str,
    allowed_relations: dict[str, str],
) -> list[dict[str, object]]:
    normalized: list[dict[str, object]] = []
    if not isinstance(entries, list):
        return normalized

    for entry in entries:
        if not isinstance(entry, dict):
            continue
        try:
            entity_id = int(entry.get(id_key))
        except (TypeError, ValueError):
            continue

        relation = _ensure_string(entry.get("relation")).strip() or "other"
        if relation not in allowed_relations:
            relation = "other"

        note = _ensure_string(entry.get("note")).strip()
        normalized.append({id_key: entity_id, "relation": relation, "note": note})

    return normalized


def parse_profile_notes(raw: object) -> tuple[dict[str, object], bool]:
    empty = _empty_profile_meta()
    if not raw:
        return empty, False

    if isinstance(raw, dict):
        parsed = raw
        structured = "bio" in parsed
    else:
        raw_text = _ensure_string(raw)
        try:
            parsed = json.loads(raw_text)
            structured = isinstance(parsed, dict) and "bio" in parsed
        except json.JSONDecodeError:
            empty["bio"] = raw_text
            return empty, False

    if not structured or not isinstance(parsed, dict):
        empty["bio"] = _ensure_string(raw)
        return empty, False

    profile_meta = _empty_profile_meta()
    profile_meta["bio"] = _ensure_string(parsed.get("bio")).strip()

    social_links: list[dict[str, str]] = []
    social_raw = parsed.get("social_links") or []
    if isinstance(social_raw, list):
        for entry in social_raw:
            if not isinstance(entry, dict):
                continue
            label = _ensure_string(entry.get("label")).strip()
            url = _ensure_string(entry.get("url")).strip()
            if url:
                social_links.append({"label": label, "url": url})
    profile_meta["social_links"] = social_links
    profile_meta["location_relations"] = _normalize_relation_entries(
        parsed.get("location_relations"),
        id_key="location_id",
        allowed_relations=MEMBER_RELATION_TYPES,
    )
    profile_meta["item_relations"] = _normalize_relation_entries(
        parsed.get("item_relations"),
        id_key="item_id",
        allowed_relations=MEMBER_ITEM_REL_TYPES,
    )
    profile_meta["event_relations"] = _normalize_relation_entries(
        parsed.get("event_relations"),
        id_key="event_id",
        allowed_relations=MEMBER_EVENT_REL_TYPES,
    )
    return profile_meta, True


def serialize_profile_notes(meta: dict[str, object]) -> str:
    payload = _empty_profile_meta()
    payload["bio"] = _ensure_string(meta.get("bio")).strip()

    social_links: list[dict[str, str]] = []
    social_raw = meta.get("social_links") or []
    if isinstance(social_raw, list):
        for entry in social_raw:
            if not isinstance(entry, dict):
                continue
            label = _ensure_string(entry.get("label")).strip()
            url = _ensure_string(entry.get("url")).strip()
            if url:
                social_links.append({"label": label, "url": url})
    payload["social_links"] = social_links
    payload["location_relations"] = _normalize_relation_entries(
        meta.get("location_relations"),
        id_key="location_id",
        allowed_relations=MEMBER_RELATION_TYPES,
    )
    payload["item_relations"] = _normalize_relation_entries(
        meta.get("item_relations"),
        id_key="item_id",
        allowed_relations=MEMBER_ITEM_REL_TYPES,
    )
    payload["event_relations"] = _normalize_relation_entries(
        meta.get("event_relations"),
        id_key="event_id",
        allowed_relations=MEMBER_EVENT_REL_TYPES,
    )
    return json.dumps(payload, ensure_ascii=False)


def _normalize_url(url: str) -> str:
    token = url.strip()
    if not token:
        return ""
    if "://" not in token and token.startswith("www."):
        return f"https://{token}"
    return token


def _parse_relation_triplets(
    ids: list[str],
    relations: list[str],
    notes: list[str],
    *,
    id_key: str,
    allowed_relations: dict[str, str],
) -> list[dict[str, object]]:
    parsed: list[dict[str, object]] = []
    for entity_id_raw, relation_raw, note_raw in zip(ids, relations, notes):
        try:
            entity_id = int(entity_id_raw)
        except (TypeError, ValueError):
            continue

        relation = _ensure_string(relation_raw).strip() or "other"
        if relation not in allowed_relations:
            relation = "other"

        parsed.append({
            id_key: entity_id,
            "relation": relation,
            "note": _ensure_string(note_raw).strip(),
        })
    return parsed


def build_profile_meta_from_form(form: Any) -> dict[str, object]:
    social_links: list[dict[str, str]] = []
    for label_raw, url_raw in zip(form.getlist("social_label"), form.getlist("social_url")):
        url = _normalize_url(_ensure_string(url_raw))
        if not url:
            continue
        social_links.append({"label": _ensure_string(label_raw).strip(), "url": url})

    return {
        "bio": _ensure_string(form.get("bio")).strip(),
        "social_links": social_links,
        "location_relations": _parse_relation_triplets(
            form.getlist("affiliation_location_id"),
            form.getlist("affiliation_relation"),
            form.getlist("affiliation_note"),
            id_key="location_id",
            allowed_relations=MEMBER_RELATION_TYPES,
        ),
        "item_relations": _parse_relation_triplets(
            form.getlist("interest_item_id"),
            form.getlist("interest_item_relation"),
            form.getlist("interest_item_note"),
            id_key="item_id",
            allowed_relations=MEMBER_ITEM_REL_TYPES,
        ),
        "event_relations": _parse_relation_triplets(
            form.getlist("event_relation_event_id"),
            form.getlist("event_relation_relation"),
            form.getlist("event_relation_note"),
            id_key="event_id",
            allowed_relations=MEMBER_EVENT_REL_TYPES,
        ),
    }


def split_owned_events(events: list[Event], *, now: datetime) -> tuple[list[Event], list[Event]]:
    upcoming = [event for event in events if event.start_time is None or event.start_time >= now]
    past = [event for event in events if event.start_time and event.start_time < now]
    return upcoming, past
