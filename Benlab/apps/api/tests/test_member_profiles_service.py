from __future__ import annotations

import json
from datetime import datetime, timedelta

from benlab_api.services.member_profiles import (
    build_profile_meta_from_form,
    parse_profile_notes,
    serialize_profile_notes,
    split_owned_events,
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


class _DummyEvent:
    def __init__(self, start_time):
        self.start_time = start_time


def test_parse_and_serialize_profile_notes() -> None:
    raw = {
        "bio": "hello",
        "social_links": [{"label": "home", "url": "https://example.com"}],
        "location_relations": [{"location_id": "1", "relation": "work", "note": "A"}],
        "item_relations": [{"item_id": 2, "relation": "favorite", "note": "B"}],
        "event_relations": [{"event_id": 3, "relation": "host", "note": "C"}],
    }
    parsed, structured = parse_profile_notes(raw)
    assert structured is True
    assert parsed["bio"] == "hello"

    text = serialize_profile_notes(parsed)
    payload = json.loads(text)
    assert payload["social_links"][0]["url"] == "https://example.com"
    assert payload["location_relations"][0]["location_id"] == 1


def test_parse_profile_notes_fallback_for_plain_text() -> None:
    parsed, structured = parse_profile_notes("plain bio")
    assert structured is False
    assert parsed["bio"] == "plain bio"


def test_build_profile_meta_from_form() -> None:
    form = _DummyForm(
        {
            "bio": " bio ",
            "social_label": ["官网", ""],
            "social_url": ["www.example.com", ""],
            "affiliation_location_id": ["1"],
            "affiliation_relation": ["work"],
            "affiliation_note": ["note"],
            "interest_item_id": ["2"],
            "interest_item_relation": ["favorite"],
            "interest_item_note": ["fav"],
            "event_relation_event_id": ["3"],
            "event_relation_relation": ["host"],
            "event_relation_note": ["owner"],
        }
    )
    meta = build_profile_meta_from_form(form)
    assert meta["bio"] == "bio"
    assert meta["social_links"] == [{"label": "官网", "url": "https://www.example.com"}]
    assert meta["location_relations"][0]["location_id"] == 1


def test_split_owned_events() -> None:
    now = datetime(2026, 2, 27, 10, 0, 0)
    events = [
        _DummyEvent(start_time=None),
        _DummyEvent(start_time=now + timedelta(hours=1)),
        _DummyEvent(start_time=now - timedelta(days=1)),
    ]
    upcoming, past = split_owned_events(events, now=now)
    assert len(upcoming) == 2
    assert len(past) == 1
