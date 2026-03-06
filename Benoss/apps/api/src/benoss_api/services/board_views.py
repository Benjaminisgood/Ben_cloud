from __future__ import annotations

from datetime import date, datetime, timedelta

from ..models import Record


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
    all_user_ids = sorted({row.user_id for row in heat_rows})

    heat: dict[int, dict[str, int]] = {}
    for row in heat_rows:
        heat.setdefault(row.user_id, {})[str(row.day)] = row.cnt

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
    return [{"name": row.name, "count": row.cnt} for row in tag_rows]


def top_public_tags_payload(tag_rows) -> list[dict]:
    return [{"tag": row.name, "count": row.cnt} for row in tag_rows]


def matrix_payload(users_out: list[dict]) -> dict[str, dict[str, int]]:
    matrix: dict[str, dict[str, int]] = {}
    for row in users_out:
        uid = str(row.get("id", "")).strip()
        if not uid:
            continue
        counts = row.get("counts", {})
        if not isinstance(counts, dict):
            matrix[uid] = {}
            continue
        matrix[uid] = {str(day): int(count or 0) for day, count in counts.items()}
    return matrix


def record_item_payload(record: Record) -> dict:
    return {
        "id": record.id,
        "visibility": record.visibility,
        "tags": record.get_tags(),
        "preview": record.preview or "",
        "created_at": record.created_at.isoformat() + "Z" if record.created_at else None,
    }


def records_list_payload(rows: list[Record], *, limit: int) -> dict:
    has_more = len(rows) > limit
    return {
        "items": [record_item_payload(record) for record in rows[:limit]],
        "has_more": has_more,
    }
