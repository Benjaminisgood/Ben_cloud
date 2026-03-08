from __future__ import annotations

import json
import sqlite3
from datetime import date, datetime, timedelta

from sqlalchemy import delete

from benprefs_api.core.config import get_settings
from benprefs_api.db.session import SessionLocal
from benprefs_api.models import PreferenceRecord
from benprefs_api.schemas.preference_record import PreferenceRecordCreate, PreferenceRecordReview
from benprefs_api.services.preference_records import create_preference_record, review_preference_record

MOCK_ADMIN = "mock_seed_admin"
MOCK_USER = "mock_seed_user"


def _ensure_legacy_tables(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS preference_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            is_current INTEGER NOT NULL DEFAULT 1,
            is_positive INTEGER NOT NULL DEFAULT 1,
            intensity INTEGER NOT NULL DEFAULT 5,
            tags TEXT,
            last_updated TEXT,
            updated_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS website_preferences (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            category TEXT,
            usage_frequency TEXT,
            intensity INTEGER NOT NULL DEFAULT 5,
            is_current INTEGER NOT NULL DEFAULT 1,
            updated_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS preference_timeline (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            item_name TEXT NOT NULL,
            event_type TEXT NOT NULL,
            happened_at TEXT NOT NULL,
            note TEXT
        );
        """
    )


def _table_count(conn: sqlite3.Connection, table_name: str) -> int:
    return int(conn.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0])


def _seed_legacy_database() -> dict[str, dict[str, int]]:
    settings = get_settings()
    settings.SOURCE_DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)

    now = datetime.now().replace(microsecond=0)
    today = date.today()

    preference_items = [
        ("Sparkling water", 1, 1, 9, "hydration,default", (now - timedelta(days=2)).isoformat(sep=" "), now.isoformat(sep=" ")),
        ("Red-eye flights", 1, 0, 9, "travel,recovery", (now - timedelta(days=8)).isoformat(sep=" "), (now - timedelta(days=7)).isoformat(sep=" ")),
        ("Cold brew", 1, 1, 7, "caffeine,morning", (now - timedelta(days=4)).isoformat(sep=" "), (now - timedelta(days=4)).isoformat(sep=" ")),
        ("Crowded malls", 1, 0, 8, "noise,weekend", (now - timedelta(days=11)).isoformat(sep=" "), (now - timedelta(days=10)).isoformat(sep=" ")),
        ("Pilates intro class", 1, 1, 6, "wellness,trial", (now - timedelta(days=1)).isoformat(sep=" "), (now - timedelta(days=1)).isoformat(sep=" ")),
        ("Window seat", 1, 1, 8, "travel,comfort", (now - timedelta(days=5)).isoformat(sep=" "), (now - timedelta(days=5)).isoformat(sep=" ")),
    ]
    website_preferences = [
        ("YouTube", "video", "daily", 8, 1, now.isoformat(sep=" ")),
        ("Notion", "workspace", "daily", 9, 1, (now - timedelta(days=1)).isoformat(sep=" ")),
        ("Xiaohongshu", "social", "weekly", 6, 1, (now - timedelta(days=3)).isoformat(sep=" ")),
        ("GitHub", "dev", "daily", 8, 1, (now - timedelta(days=2)).isoformat(sep=" ")),
        ("Douban", "media", "monthly", 5, 1, (now - timedelta(days=9)).isoformat(sep=" ")),
    ]
    preference_timeline = [
        ("Sparkling water", "confirmed", (today - timedelta(days=30)).isoformat(), "Stayed stable for a month."),
        ("Cold brew", "boosted", (today - timedelta(days=24)).isoformat(), "Morning focus improved."),
        ("Crowded malls", "avoided", (today - timedelta(days=20)).isoformat(), "Weekend overload."),
        ("Window seat", "confirmed", (today - timedelta(days=14)).isoformat(), "Less travel fatigue."),
        ("Pilates intro class", "interested", (today - timedelta(days=6)).isoformat(), "Added to next month ideas."),
        ("Red-eye flights", "retired", (today - timedelta(days=3)).isoformat(), "Hard stop after the last trip."),
    ]

    with sqlite3.connect(settings.SOURCE_DATABASE_PATH) as conn:
        _ensure_legacy_tables(conn)
        stats = {
            "preference_items": {"existing": _table_count(conn, "preference_items"), "inserted": 0},
            "website_preferences": {"existing": _table_count(conn, "website_preferences"), "inserted": 0},
            "preference_timeline": {"existing": _table_count(conn, "preference_timeline"), "inserted": 0},
        }
        if stats["preference_items"]["existing"] == 0:
            conn.executemany(
                """
                INSERT INTO preference_items
                    (name, is_current, is_positive, intensity, tags, last_updated, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                preference_items,
            )
            stats["preference_items"]["inserted"] = len(preference_items)
        if stats["website_preferences"]["existing"] == 0:
            conn.executemany(
                """
                INSERT INTO website_preferences
                    (name, category, usage_frequency, intensity, is_current, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                website_preferences,
            )
            stats["website_preferences"]["inserted"] = len(website_preferences)
        if stats["preference_timeline"]["existing"] == 0:
            conn.executemany(
                """
                INSERT INTO preference_timeline
                    (item_name, event_type, happened_at, note)
                VALUES (?, ?, ?, ?)
                """,
                preference_timeline,
            )
            stats["preference_timeline"]["inserted"] = len(preference_timeline)
        conn.commit()
    return stats


def _serialize_record(record: PreferenceRecord) -> dict[str, str | int | None]:
    return {
        "id": record.id,
        "subject_name": record.subject_name,
        "stance": record.stance,
        "review_status": record.review_status,
        "created_by": record.created_by,
        "reviewed_by": record.reviewed_by,
        "reviewed_at": record.reviewed_at.isoformat() if record.reviewed_at else None,
    }


def _seed_records() -> list[dict[str, str | int | None]]:
    today = date.today()
    specs = [
        {
            "actor": MOCK_ADMIN,
            "role": "admin",
            "payload": PreferenceRecordCreate(
                subject_type="drink",
                subject_name="Sparkling water",
                aspect="default drink",
                stance="love",
                timeframe="current",
                validation_state="confirmed",
                intensity=9,
                certainty=8,
                context="Default fridge pick after lunch",
                merchant_name="Trader Joes",
                source_kind="observation",
                trigger_detail="Repeatedly chosen over soda and juice.",
                supporting_detail="No sugar crash and easy to restock.",
                valid_from=today - timedelta(days=40),
            ),
        },
        {
            "actor": MOCK_ADMIN,
            "role": "admin",
            "payload": PreferenceRecordCreate(
                subject_type="service",
                subject_name="Notion dashboards",
                aspect="workspace setup",
                stance="like",
                timeframe="current",
                validation_state="confirmed",
                intensity=8,
                certainty=8,
                context="Useful for weekly planning",
                source_kind="manual",
                trigger_detail="Keeps notes and tasks in one place.",
                supporting_detail="Still preferred over fragmented tools.",
                valid_from=today - timedelta(days=75),
            ),
        },
        {
            "actor": MOCK_USER,
            "role": "user",
            "payload": PreferenceRecordCreate(
                subject_type="activity",
                subject_name="Pilates intro class",
                aspect="new class trial",
                stance="want_to_try",
                timeframe="future",
                validation_state="hypothesis",
                intensity=6,
                certainty=5,
                context="Considering a weekday evening slot",
                source_kind="journal",
                trigger_detail="Looking for lower-impact movement options.",
                supporting_detail="Need a beginner-friendly studio nearby.",
                valid_from=today + timedelta(days=7),
            ),
        },
        {
            "actor": MOCK_USER,
            "role": "user",
            "payload": PreferenceRecordCreate(
                subject_type="food",
                subject_name="Overnight oats",
                aspect="weekday breakfast",
                stance="like",
                timeframe="current",
                validation_state="confirmed",
                intensity=7,
                certainty=7,
                context="Works well before early meetings",
                source_kind="observation",
                trigger_detail="Better energy curve than toast-only breakfast.",
                supporting_detail="Easy to prep the night before.",
                valid_from=today - timedelta(days=18),
            ),
            "review": PreferenceRecordReview(
                review_status="approved",
            ),
        },
        {
            "actor": MOCK_ADMIN,
            "role": "admin",
            "payload": PreferenceRecordCreate(
                subject_type="environment",
                subject_name="Crowded malls",
                aspect="weekend errands",
                stance="avoid",
                timeframe="current",
                validation_state="confirmed",
                intensity=8,
                certainty=9,
                context="Noise and waiting time both stack up",
                source_kind="memory",
                trigger_detail="Short visits consistently feel draining.",
                supporting_detail="Smaller neighborhood stores work better.",
                valid_from=today - timedelta(days=120),
            ),
        },
        {
            "actor": MOCK_USER,
            "role": "user",
            "payload": PreferenceRecordCreate(
                subject_type="activity",
                subject_name="5am running",
                aspect="early cardio",
                stance="avoid",
                timeframe="future",
                validation_state="conflicted",
                intensity=8,
                certainty=6,
                context="Too much recovery debt after poor sleep",
                source_kind="manual",
                trigger_detail="The routine looked good on paper but felt unsustainable.",
                supporting_detail="Energy and mood both dipped after three attempts.",
                valid_from=today + timedelta(days=1),
            ),
        },
    ]

    with SessionLocal() as db:
        db.execute(delete(PreferenceRecord).where(PreferenceRecord.created_by.in_((MOCK_ADMIN, MOCK_USER))))
        db.commit()

        records: list[PreferenceRecord] = []
        for spec in specs:
            item = create_preference_record(
                db,
                payload=spec["payload"],
                actor=spec["actor"],
                actor_role=spec["role"],
            )
            review = spec.get("review")
            if review:
                item = review_preference_record(
                    db,
                    record_id=item.id,
                    payload=review,
                    actor=MOCK_ADMIN,
                )
            records.append(item)
        return [_serialize_record(record) for record in records]


def main() -> int:
    settings = get_settings()
    settings.ensure_data_dirs()
    result = {
        "source_db": str(settings.SOURCE_DATABASE_PATH),
        "legacy": _seed_legacy_database(),
        "records": _seed_records(),
    }
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
