from __future__ import annotations

from datetime import datetime, timedelta

from benlab_api.services.event_views import build_event_summary, parse_feedback_entries, split_events_by_time


class _DummyLink:
    def __init__(self, member_id: int):
        self.member_id = member_id


class _DummyEvent:
    def __init__(self, start_time=None, end_time=None, participant_ids: list[int] | None = None):
        self.start_time = start_time
        self.end_time = end_time
        self.participant_links = [_DummyLink(member_id) for member_id in (participant_ids or [])]


def test_split_events_by_time() -> None:
    now = datetime(2026, 2, 27, 12, 0, 0)
    events = [
        _DummyEvent(start_time=now - timedelta(days=2), end_time=now - timedelta(days=1)),
        _DummyEvent(start_time=now + timedelta(hours=2), end_time=None),
        _DummyEvent(start_time=None, end_time=None),
    ]
    upcoming, past = split_events_by_time(events, now=now)
    assert len(upcoming) == 2
    assert len(past) == 1


def test_build_event_summary() -> None:
    now = datetime(2026, 2, 27, 12, 0, 0)
    events = [
        _DummyEvent(start_time=now - timedelta(hours=1), end_time=now + timedelta(hours=1), participant_ids=[1, 2]),
        _DummyEvent(start_time=None, end_time=None, participant_ids=[2, 3]),
        _DummyEvent(start_time=now - timedelta(days=1), end_time=now - timedelta(hours=2), participant_ids=[4]),
    ]
    summary = build_event_summary(events, now=now)
    assert summary == {
        "total": 3,
        "ongoing": 1,
        "upcoming": 0,
        "unscheduled": 1,
        "past": 1,
        "participants": 4,
    }


def test_parse_feedback_entries() -> None:
    log = "2026-02-27T12:00:00|alice|ok\nbroken-line\n2026-02-27T12:01:00|bob|done"
    out = parse_feedback_entries(log)
    assert len(out) == 2
    assert out[0]["sender"] == "alice"
    assert out[1]["content"] == "done"
