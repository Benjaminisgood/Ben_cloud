from __future__ import annotations

from datetime import datetime

from benlab_api.models import Event


def split_events_by_time(events: list[Event], *, now: datetime) -> tuple[list[Event], list[Event]]:
    upcoming_events: list[Event] = []
    past_events: list[Event] = []
    for event in events:
        if event.start_time and event.start_time < now and event.end_time and event.end_time < now:
            past_events.append(event)
        elif event.start_time and event.start_time < now and event.end_time is None:
            upcoming_events.append(event)
        elif event.start_time is None:
            upcoming_events.append(event)
        elif event.start_time >= now:
            upcoming_events.append(event)
        else:
            past_events.append(event)
    return upcoming_events, past_events


def build_event_summary(events: list[Event], *, now: datetime) -> dict[str, int]:
    summary = {"total": 0, "ongoing": 0, "upcoming": 0, "unscheduled": 0, "past": 0, "participants": 0}
    participant_ids: set[int] = set()
    for event in events:
        summary["total"] += 1
        for link in event.participant_links:
            participant_ids.add(link.member_id)

        if event.start_time is None:
            summary["unscheduled"] += 1
        elif event.start_time <= now and (event.end_time is None or event.end_time >= now):
            summary["ongoing"] += 1
        elif event.start_time > now:
            summary["upcoming"] += 1
        else:
            summary["past"] += 1

    summary["participants"] = len(participant_ids)
    return summary


def parse_feedback_entries(feedback_log: str) -> list[dict[str, str]]:
    entries: list[dict[str, str]] = []
    for raw in (feedback_log or "").splitlines():
        if not raw.strip():
            continue
        parts = raw.split("|", 2)
        if len(parts) == 3:
            entries.append({"timestamp": parts[0], "sender": parts[1], "content": parts[2]})
    return entries
