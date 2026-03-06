from __future__ import annotations

from datetime import date, datetime, timedelta

from benlab_api.models import Message
from benlab_api.services.records_service import extract_tags_from_message, preview_text


def clamp_days(days: int, *, default_days: int) -> int:
    if days <= 0:
        days = default_days
    return max(1, min(days, 366))


def day_start(value: date) -> datetime:
    return datetime(value.year, value.month, value.day)


def parse_day(day: str) -> date:
    return datetime.strptime(day, "%Y-%m-%d").date()


def build_date_range(*, start_date: date, days: int) -> list[str]:
    return [(start_date + timedelta(days=i)).isoformat() for i in range(days)]


def build_users_heat(
    *,
    heat_rows,
    users_map: dict[int, str],
    date_range: list[str],
) -> list[dict]:
    all_user_ids = sorted({int(row.user_id) for row in heat_rows})

    heat: dict[int, dict[str, int]] = {}
    for row in heat_rows:
        uid = int(row.user_id)
        heat.setdefault(uid, {})[str(row.day)] = int(row.cnt)

    users_out = [
        {
            "id": uid,
            "username": users_map.get(uid, str(uid)),
            "counts": {d: heat.get(uid, {}).get(d, 0) for d in date_range},
            "total": sum(heat.get(uid, {}).values()),
        }
        for uid in all_user_ids
    ]
    users_out.sort(key=lambda row: -row["total"])
    return users_out


def top_tags_payload(tag_rows) -> list[dict]:
    out: list[dict] = []
    for row in tag_rows:
        if isinstance(row, tuple):
            name, count = row
        else:
            name = getattr(row, "name", "")
            count = getattr(row, "cnt", 0)
        out.append({"name": str(name), "count": int(count)})
    return out


def record_item_payload(record: Message) -> dict:
    return {
        "id": record.id,
        "visibility": "private",
        "tags": extract_tags_from_message(record),
        "preview": preview_text(record.content or ""),
        "created_at": record.timestamp.isoformat() + "Z" if record.timestamp else None,
    }


def records_list_payload(rows: list[Message], *, limit: int) -> dict:
    has_more = len(rows) > limit
    return {
        "items": [record_item_payload(record) for record in rows[:limit]],
        "has_more": has_more,
    }
