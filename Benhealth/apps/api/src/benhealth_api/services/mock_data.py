from __future__ import annotations

import json
import sqlite3
from datetime import date, datetime, timedelta

from sqlalchemy import delete

from benhealth_api.core.config import get_settings
from benhealth_api.db.session import SessionLocal
from benhealth_api.models import HealthRecord
from benhealth_api.schemas.health_record import HealthRecordCreate, HealthRecordReview
from benhealth_api.services.health_records import create_health_record, review_health_record

MOCK_ADMIN = "mock_seed_admin"
MOCK_USER = "mock_seed_user"


def _ensure_legacy_tables(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS workouts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            start_time TEXT NOT NULL,
            duration_minutes INTEGER NOT NULL,
            intensity TEXT,
            post_workout_mood TEXT
        );

        CREATE TABLE IF NOT EXISTS daily_nutrition_summary (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            total_calories REAL,
            total_protein REAL,
            water_ml REAL
        );

        CREATE TABLE IF NOT EXISTS health_goals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            status TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS body_metrics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            recorded_at TEXT NOT NULL,
            weight REAL,
            bmi REAL,
            resting_heart_rate INTEGER
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

    workouts = [
        ((now - timedelta(days=1, hours=2)).isoformat(sep=" "), 45, "medium", "steady"),
        ((now - timedelta(days=2, hours=1)).isoformat(sep=" "), 35, "light", "clear"),
        ((now - timedelta(days=4, hours=3)).isoformat(sep=" "), 62, "hard", "tired"),
        ((now - timedelta(days=6, hours=2)).isoformat(sep=" "), 28, "light", "better"),
        ((now - timedelta(days=8, hours=4)).isoformat(sep=" "), 50, "medium", "good"),
        ((now - timedelta(days=10, hours=1)).isoformat(sep=" "), 40, "medium", "calm"),
    ]
    nutrition_days = [
        ((today - timedelta(days=1)).isoformat(), 2180, 132.0, 2400),
        ((today - timedelta(days=2)).isoformat(), 2050, 118.0, 2200),
        ((today - timedelta(days=3)).isoformat(), 2310, 140.0, 2500),
        ((today - timedelta(days=4)).isoformat(), 1985, 110.0, 2100),
        ((today - timedelta(days=5)).isoformat(), 2240, 128.0, 2350),
    ]
    health_goals = [
        ("Sleep before 23:30", "active"),
        ("Two zone-2 rides weekly", "active"),
        ("Vitamin D retest", "active"),
        ("5am wakeup experiment", "paused"),
    ]
    body_metrics = [
        ((now - timedelta(days=1)).isoformat(sep=" "), 72.4, 22.8, 58),
        ((now - timedelta(days=4)).isoformat(sep=" "), 72.8, 22.9, 60),
        ((now - timedelta(days=7)).isoformat(sep=" "), 73.0, 23.0, 61),
        ((now - timedelta(days=10)).isoformat(sep=" "), 73.2, 23.1, 62),
    ]

    with sqlite3.connect(settings.SOURCE_DATABASE_PATH) as conn:
        _ensure_legacy_tables(conn)
        stats = {
            "workouts": {"existing": _table_count(conn, "workouts"), "inserted": 0},
            "daily_nutrition_summary": {"existing": _table_count(conn, "daily_nutrition_summary"), "inserted": 0},
            "health_goals": {"existing": _table_count(conn, "health_goals"), "inserted": 0},
            "body_metrics": {"existing": _table_count(conn, "body_metrics"), "inserted": 0},
        }
        if stats["workouts"]["existing"] == 0:
            conn.executemany(
                """
                INSERT INTO workouts
                    (start_time, duration_minutes, intensity, post_workout_mood)
                VALUES (?, ?, ?, ?)
                """,
                workouts,
            )
            stats["workouts"]["inserted"] = len(workouts)
        if stats["daily_nutrition_summary"]["existing"] == 0:
            conn.executemany(
                """
                INSERT INTO daily_nutrition_summary
                    (date, total_calories, total_protein, water_ml)
                VALUES (?, ?, ?, ?)
                """,
                nutrition_days,
            )
            stats["daily_nutrition_summary"]["inserted"] = len(nutrition_days)
        if stats["health_goals"]["existing"] == 0:
            conn.executemany(
                """
                INSERT INTO health_goals
                    (title, status)
                VALUES (?, ?)
                """,
                health_goals,
            )
            stats["health_goals"]["inserted"] = len(health_goals)
        if stats["body_metrics"]["existing"] == 0:
            conn.executemany(
                """
                INSERT INTO body_metrics
                    (recorded_at, weight, bmi, resting_heart_rate)
                VALUES (?, ?, ?, ?)
                """,
                body_metrics,
            )
            stats["body_metrics"]["inserted"] = len(body_metrics)
        conn.commit()
    return stats


def _serialize_record(record: HealthRecord) -> dict[str, str | int | float | None]:
    return {
        "id": record.id,
        "title": record.title,
        "domain": record.domain,
        "review_status": record.review_status,
        "created_by": record.created_by,
        "reviewed_by": record.reviewed_by,
        "reviewed_at": record.reviewed_at.isoformat() if record.reviewed_at else None,
    }


def _seed_records() -> list[dict[str, str | int | float | None]]:
    today = date.today()
    specs = [
        {
            "actor": MOCK_ADMIN,
            "role": "admin",
            "payload": HealthRecordCreate(
                domain="exercise",
                title="Zone 2 cycling block",
                summary="Two steady rides are keeping recovery and focus balanced.",
                care_status="active",
                concern_level="medium",
                started_on=today - timedelta(days=21),
                next_review_on=today + timedelta(days=6),
                frequency="weekly",
                metric_name="avg_hr",
                metric_value=136,
                metric_unit="bpm",
                mood_score=7,
                energy_score=8,
                sleep_hours=7.4,
                exercise_name="Outdoor ride",
                follow_up_plan="Hold the current volume for one more week.",
            ),
        },
        {
            "actor": MOCK_ADMIN,
            "role": "admin",
            "payload": HealthRecordCreate(
                domain="diet",
                title="Protein at breakfast",
                summary="High-protein breakfasts reduce the mid-morning crash.",
                care_status="stable",
                concern_level="low",
                started_on=today - timedelta(days=28),
                next_review_on=today + timedelta(days=10),
                frequency="daily",
                metric_name="protein",
                metric_value=32,
                metric_unit="g",
                mood_score=7,
                energy_score=8,
                food_name="Greek yogurt bowl",
                follow_up_plan="Keep rotating simple options to avoid boredom.",
            ),
        },
        {
            "actor": MOCK_USER,
            "role": "user",
            "payload": HealthRecordCreate(
                domain="medical",
                title="Vitamin D retest",
                summary="Need a lab follow-up after the last borderline result.",
                care_status="needs_attention",
                concern_level="high",
                started_on=today - timedelta(days=9),
                next_review_on=today + timedelta(days=4),
                frequency="once",
                provider_name="CityMed",
                medication_name="Vitamin D3",
                follow_up_plan="Book the lab and bring the previous panel.",
                agent_note="Pending scheduling confirmation.",
            ),
        },
        {
            "actor": MOCK_USER,
            "role": "user",
            "payload": HealthRecordCreate(
                domain="mental",
                title="Post-lunch focus dip",
                summary="Focus drops between 14:00 and 15:00 on low-sleep days.",
                care_status="active",
                concern_level="medium",
                started_on=today - timedelta(days=12),
                next_review_on=today + timedelta(days=5),
                frequency="daily",
                mood_score=6,
                energy_score=5,
                sleep_hours=6.6,
                follow_up_plan="Track lunch size, caffeine cutoff, and walking breaks.",
            ),
            "review": HealthRecordReview(
                review_status="approved",
            ),
        },
        {
            "actor": MOCK_ADMIN,
            "role": "admin",
            "payload": HealthRecordCreate(
                domain="diet",
                title="Late coffee cutoff",
                summary="Stopping caffeine after 14:00 improves sleep depth on most nights.",
                care_status="active",
                concern_level="low",
                started_on=today - timedelta(days=18),
                next_review_on=today + timedelta(days=7),
                frequency="daily",
                metric_name="cutoff",
                metric_value=14,
                metric_unit="h",
                mood_score=7,
                energy_score=7,
                sleep_hours=7.8,
                food_name="Cold brew",
                follow_up_plan="Keep a decaf fallback for late meetings.",
            ),
        },
        {
            "actor": MOCK_USER,
            "role": "user",
            "payload": HealthRecordCreate(
                domain="habit",
                title="5am wakeup retry",
                summary="The current sleep debt makes another early wakeup sprint look risky.",
                care_status="planned",
                concern_level="medium",
                next_review_on=today + timedelta(days=14),
                frequency="daily",
                mood_score=5,
                energy_score=4,
                sleep_hours=6.1,
                follow_up_plan="Revisit only after seven stable nights.",
            ),
        },
    ]

    with SessionLocal() as db:
        db.execute(delete(HealthRecord).where(HealthRecord.created_by.in_((MOCK_ADMIN, MOCK_USER))))
        db.commit()

        records: list[HealthRecord] = []
        for spec in specs:
            item = create_health_record(
                db,
                payload=spec["payload"],
                actor=spec["actor"],
                actor_role=spec["role"],
            )
            review = spec.get("review")
            if review:
                item = review_health_record(
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
