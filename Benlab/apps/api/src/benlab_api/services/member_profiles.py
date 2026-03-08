from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from benlab_api.models import Event

MEMBER_GENDER_TYPES = {
    "female": "女",
    "male": "男",
    "nonbinary": "非二元",
    "other": "其他",
    "unknown": "未标注",
}
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


def _normalize_choice(value: object | None, *, allowed: dict[str, str], default: str = "") -> str:
    token = _ensure_string(value).strip()
    if not token:
        return default
    return token if token in allowed else default


def _normalize_date(value: object | None) -> str:
    token = _ensure_string(value).strip()
    if not token:
        return ""
    try:
        return datetime.strptime(token, "%Y-%m-%d").date().isoformat()
    except ValueError:
        return ""


def _normalize_birthyear(value: object | None) -> int | None:
    token = _ensure_string(value).strip()
    if not token:
        return None
    try:
        year = int(token)
    except (TypeError, ValueError):
        return None
    if 1900 <= year <= 2100:
        return year
    return None


def _empty_first_met() -> dict[str, str]:
    return {
        "date": "",
        "location": "",
        "feeling": "",
        "story": "",
    }


def _normalize_first_met(value: object) -> dict[str, str]:
    payload = _empty_first_met()
    if not isinstance(value, dict):
        return payload
    payload["date"] = _normalize_date(value.get("date"))
    payload["location"] = _ensure_string(value.get("location")).strip()
    payload["feeling"] = _ensure_string(value.get("feeling")).strip()
    payload["story"] = _ensure_string(value.get("story")).strip()
    return payload


def _empty_profile_meta() -> dict[str, object]:
    return {
        "bio": "",
        "nickname": "",
        "gender": "",
        "birthday": "",
        "birthyear": None,
        "relationship_label": "",
        "first_met": _empty_first_met(),
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
    profile_meta["nickname"] = _ensure_string(parsed.get("nickname")).strip()
    profile_meta["gender"] = _normalize_choice(parsed.get("gender"), allowed=MEMBER_GENDER_TYPES)
    profile_meta["birthday"] = _normalize_date(parsed.get("birthday"))
    profile_meta["birthyear"] = _normalize_birthyear(parsed.get("birthyear"))
    profile_meta["relationship_label"] = _ensure_string(parsed.get("relationship_label")).strip()
    profile_meta["first_met"] = _normalize_first_met(parsed.get("first_met"))

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
    payload["nickname"] = _ensure_string(meta.get("nickname")).strip()
    payload["gender"] = _normalize_choice(meta.get("gender"), allowed=MEMBER_GENDER_TYPES)
    payload["birthday"] = _normalize_date(meta.get("birthday"))
    payload["birthyear"] = _normalize_birthyear(meta.get("birthyear"))
    payload["relationship_label"] = _ensure_string(meta.get("relationship_label")).strip()
    payload["first_met"] = _normalize_first_met(meta.get("first_met"))

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


def build_profile_meta_from_form(
    form: Any,
    *,
    base_meta: dict[str, object] | None = None,
    include_admin_connection_fields: bool = True,
) -> dict[str, object]:
    social_links: list[dict[str, str]] = []
    for label_raw, url_raw in zip(form.getlist("social_label"), form.getlist("social_url")):
        url = _normalize_url(_ensure_string(url_raw))
        if not url:
            continue
        social_links.append({"label": _ensure_string(label_raw).strip(), "url": url})

    profile_meta = parse_profile_notes(base_meta or _empty_profile_meta())[0]

    payload = {
        "bio": _ensure_string(form.get("bio")).strip(),
        "nickname": _ensure_string(form.get("nickname")).strip(),
        "gender": _normalize_choice(form.get("gender"), allowed=MEMBER_GENDER_TYPES),
        "birthday": _normalize_date(form.get("birthday")),
        "birthyear": _normalize_birthyear(form.get("birthyear")),
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
    if include_admin_connection_fields:
        payload["relationship_label"] = _ensure_string(form.get("relationship_label")).strip()
        payload["first_met"] = _normalize_first_met(
            {
                "date": form.get("first_met_date"),
                "location": form.get("first_met_location"),
                "feeling": form.get("first_met_feeling"),
                "story": form.get("first_met_story"),
            }
        )
    else:
        payload["relationship_label"] = _ensure_string(profile_meta.get("relationship_label")).strip()
        payload["first_met"] = _normalize_first_met(profile_meta.get("first_met"))
    return payload


def collect_profile_relation_ids(meta: dict[str, object]) -> dict[str, list[int]]:
    def _ids(entries: object, *, key: str) -> list[int]:
        values: list[int] = []
        if not isinstance(entries, list):
            return values
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            try:
                values.append(int(entry[key]))
            except (KeyError, TypeError, ValueError):
                continue
        return values

    return {
        "location_ids": _ids(meta.get("location_relations"), key="location_id"),
        "item_ids": _ids(meta.get("item_relations"), key="item_id"),
        "event_ids": _ids(meta.get("event_relations"), key="event_id"),
    }


def _build_relation_view_entries(
    entries: object,
    *,
    id_key: str,
    object_key: str,
    objects: list[object],
    allowed_relations: dict[str, str],
) -> list[dict[str, object]]:
    if not isinstance(entries, list):
        return []
    objects_by_id = {getattr(obj, "id", None): obj for obj in objects}
    rows: list[dict[str, object]] = []
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        entity = objects_by_id.get(entry.get(id_key))
        if entity is None:
            continue
        relation = _ensure_string(entry.get("relation")).strip() or "other"
        rows.append(
            {
                object_key: entity,
                "relation": relation,
                "relation_label": allowed_relations.get(relation, allowed_relations.get("other", "其他")),
                "note": _ensure_string(entry.get("note")).strip(),
            }
        )
    return rows


def build_profile_relation_sections(
    meta: dict[str, object],
    *,
    locations: list[object],
    items: list[object],
    events: list[object],
) -> dict[str, list[dict[str, object]]]:
    return {
        "locations": _build_relation_view_entries(
            meta.get("location_relations"),
            id_key="location_id",
            object_key="location",
            objects=locations,
            allowed_relations=MEMBER_RELATION_TYPES,
        ),
        "items": _build_relation_view_entries(
            meta.get("item_relations"),
            id_key="item_id",
            object_key="item",
            objects=items,
            allowed_relations=MEMBER_ITEM_REL_TYPES,
        ),
        "events": _build_relation_view_entries(
            meta.get("event_relations"),
            id_key="event_id",
            object_key="event",
            objects=events,
            allowed_relations=MEMBER_EVENT_REL_TYPES,
        ),
    }


def build_member_overview(meta: dict[str, object]) -> dict[str, object]:
    birthday = _normalize_date(meta.get("birthday"))
    birthyear = _normalize_birthyear(meta.get("birthyear"))
    first_met = _normalize_first_met(meta.get("first_met"))
    first_met_parts = [part for part in [first_met.get("date"), first_met.get("location")] if part]
    return {
        "nickname": _ensure_string(meta.get("nickname")).strip(),
        "gender": _normalize_choice(meta.get("gender"), allowed=MEMBER_GENDER_TYPES),
        "gender_label": MEMBER_GENDER_TYPES.get(_normalize_choice(meta.get("gender"), allowed=MEMBER_GENDER_TYPES), ""),
        "birthday": birthday,
        "birthyear": birthyear,
        "birthday_label": birthday or (f"{birthyear} 年" if birthyear else ""),
        "relationship_label": _ensure_string(meta.get("relationship_label")).strip(),
        "first_met": first_met,
        "first_met_summary": " / ".join(first_met_parts),
    }


def build_member_listing_cards(
    members: list[object],
    *,
    followed_ids: set[int],
    viewer_is_admin: bool,
) -> list[dict[str, object]]:
    cards: list[dict[str, object]] = []
    for member in members:
        profile_meta, _ = parse_profile_notes(getattr(member, "notes", ""))
        overview = build_member_overview(profile_meta)
        item_count = (
            len(profile_meta.get("item_relations", []))
            if viewer_is_admin
            else len(getattr(member, "items", []) or [])
        )
        location_count = (
            len(profile_meta.get("location_relations", []))
            if viewer_is_admin
            else len(getattr(member, "responsible_locations", []) or [])
        )
        connection_count = len(getattr(member, "outbound_connections", []) or []) if viewer_is_admin else 0
        summary_tokens = [
            getattr(member, "name", "") or "",
            getattr(member, "username", "") or "",
            getattr(member, "contact", "") or "",
            _ensure_string(overview.get("nickname")),
        ]
        if viewer_is_admin:
            summary_tokens.extend(
                [
                    _ensure_string(overview.get("relationship_label")),
                    _ensure_string(overview.get("birthday_label")),
                    _ensure_string(overview.get("first_met_summary")),
                    _ensure_string(overview.get("gender_label")),
                    _ensure_string(
                        overview.get("first_met", {}).get("feeling")
                        if isinstance(overview.get("first_met"), dict)
                        else ""
                    ),
                    _ensure_string(
                        overview.get("first_met", {}).get("story")
                        if isinstance(overview.get("first_met"), dict)
                        else ""
                    ),
                ]
            )
        cards.append(
            {
                "member": member,
                "overview": overview,
                "item_count": item_count,
                "location_count": location_count,
                "connection_count": connection_count,
                "is_following": getattr(member, "id", None) in followed_ids,
                "search_blob": " ".join(token for token in summary_tokens if token).lower(),
            }
        )
    return cards


def split_owned_events(events: list[Event], *, now: datetime) -> tuple[list[Event], list[Event]]:
    upcoming = [event for event in events if event.start_time is None or event.start_time >= now]
    past = [event for event in events if event.start_time and event.start_time < now]
    return upcoming, past
