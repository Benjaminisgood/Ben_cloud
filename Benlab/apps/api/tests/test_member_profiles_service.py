from __future__ import annotations

import json
from datetime import datetime, timedelta

from benlab_api.services.member_profiles import (
    build_member_listing_cards,
    build_member_overview,
    build_profile_meta_from_form,
    build_profile_relation_sections,
    collect_profile_relation_ids,
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
        "nickname": "阿博",
        "gender": "male",
        "birthday": "1994-06-18",
        "birthyear": "1994",
        "relationship_label": "大学同学",
        "first_met": {
            "date": "2012-09-01",
            "location": "宿舍楼",
            "feeling": "很能聊",
            "story": "报到第一天遇到",
        },
        "social_links": [{"label": "home", "url": "https://example.com"}],
        "location_relations": [{"location_id": "1", "relation": "work", "note": "A"}],
        "item_relations": [{"item_id": 2, "relation": "favorite", "note": "B"}],
        "event_relations": [{"event_id": 3, "relation": "host", "note": "C"}],
    }
    parsed, structured = parse_profile_notes(raw)
    assert structured is True
    assert parsed["bio"] == "hello"
    assert parsed["nickname"] == "阿博"
    assert parsed["gender"] == "male"
    assert parsed["birthyear"] == 1994
    assert parsed["relationship_label"] == "大学同学"
    assert parsed["first_met"]["location"] == "宿舍楼"

    text = serialize_profile_notes(parsed)
    payload = json.loads(text)
    assert payload["social_links"][0]["url"] == "https://example.com"
    assert payload["location_relations"][0]["location_id"] == 1
    assert payload["birthday"] == "1994-06-18"
    assert payload["first_met"]["story"] == "报到第一天遇到"


def test_parse_profile_notes_fallback_for_plain_text() -> None:
    parsed, structured = parse_profile_notes("plain bio")
    assert structured is False
    assert parsed["bio"] == "plain bio"


def test_build_profile_meta_from_form() -> None:
    form = _DummyForm(
        {
            "bio": " bio ",
            "nickname": " 小博 ",
            "gender": "male",
            "birthday": "1994-06-18",
            "birthyear": "1994",
            "relationship_label": "朋友",
            "first_met_date": "2012-09-01",
            "first_met_location": "学校",
            "first_met_feeling": "很投缘",
            "first_met_story": "开学认识",
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
    assert meta["nickname"] == "小博"
    assert meta["gender"] == "male"
    assert meta["birthyear"] == 1994
    assert meta["social_links"] == [{"label": "官网", "url": "https://www.example.com"}]
    assert meta["location_relations"][0]["location_id"] == 1
    assert meta["relationship_label"] == "朋友"
    assert meta["first_met"]["story"] == "开学认识"


def test_build_profile_meta_from_form_preserves_admin_fields() -> None:
    base_meta = {
        "bio": "old",
        "relationship_label": "老朋友",
        "first_met": {
            "date": "2010-01-01",
            "location": "北京",
            "feeling": "熟悉",
            "story": "很久以前认识",
        },
    }
    form = _DummyForm(
        {
            "bio": "new bio",
            "nickname": "Ben",
            "social_label": [],
            "social_url": [],
            "affiliation_location_id": [],
            "affiliation_relation": [],
            "affiliation_note": [],
            "interest_item_id": [],
            "interest_item_relation": [],
            "interest_item_note": [],
            "event_relation_event_id": [],
            "event_relation_relation": [],
            "event_relation_note": [],
        }
    )
    meta = build_profile_meta_from_form(form, base_meta=base_meta, include_admin_connection_fields=False)
    assert meta["bio"] == "new bio"
    assert meta["relationship_label"] == "老朋友"
    assert meta["first_met"]["location"] == "北京"


def test_build_profile_relations_and_listing_cards() -> None:
    profile_meta = {
        "nickname": "阿博",
        "gender": "male",
        "birthday": "1994-06-18",
        "relationship_label": "大学同学",
        "first_met": {"date": "2012-09-01", "location": "宿舍楼", "feeling": "", "story": ""},
        "location_relations": [{"location_id": 10, "relation": "live", "note": "一起住过"}],
        "item_relations": [{"item_id": 20, "relation": "favorite", "note": "一起买的"}],
        "event_relations": [{"event_id": 30, "relation": "join", "note": "一起参加"}],
    }
    relation_ids = collect_profile_relation_ids(profile_meta)
    assert relation_ids == {"location_ids": [10], "item_ids": [20], "event_ids": [30]}

    location = type("Location", (), {"id": 10, "name": "上海", "status": "正常"})()
    item = type("Item", (), {"id": 20, "name": "相机", "status": "正常"})()
    event = type("Event", (), {"id": 30, "title": "毕业旅行"})()
    sections = build_profile_relation_sections(profile_meta, locations=[location], items=[item], events=[event])
    assert sections["locations"][0]["location"].name == "上海"
    assert sections["items"][0]["relation_label"] == "收藏"
    assert sections["events"][0]["event"].title == "毕业旅行"

    member = type(
        "Member",
        (),
        {
            "id": 1,
            "name": "Ben",
            "username": "ben",
            "contact": "123",
            "notes": serialize_profile_notes(profile_meta),
            "items": [],
            "responsible_locations": [],
        },
    )()
    cards = build_member_listing_cards([member], followed_ids={1}, viewer_is_admin=True)
    assert cards[0]["item_count"] == 1
    assert cards[0]["location_count"] == 1
    assert cards[0]["overview"]["relationship_label"] == "大学同学"
    assert "宿舍楼" in cards[0]["search_blob"]


def test_build_member_overview_formats_fields() -> None:
    overview = build_member_overview(
        {
            "nickname": "阿博",
            "gender": "male",
            "birthday": "1994-06-18",
            "birthyear": "1994",
            "relationship_label": "同学",
            "first_met": {"date": "2012-09-01", "location": "宿舍楼"},
        }
    )
    assert overview["gender_label"] == "男"
    assert overview["birthday_label"] == "1994-06-18"
    assert overview["first_met_summary"] == "2012-09-01 / 宿舍楼"


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
