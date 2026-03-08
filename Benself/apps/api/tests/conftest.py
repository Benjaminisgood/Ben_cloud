
from __future__ import annotations

import importlib
import os
import sqlite3
import sys
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient

API_SRC_DIR = Path(__file__).resolve().parents[1] / "src"
if str(API_SRC_DIR) not in sys.path:
    sys.path.insert(0, str(API_SRC_DIR))


def _run_migrations(database_url: str) -> None:
    config = Config(str(Path(__file__).resolve().parents[1] / "alembic.ini"))
    config.set_main_option("sqlalchemy.url", database_url)
    command.upgrade(config, "head")


def _seed_journals_db(path: Path) -> None:
    with sqlite3.connect(path) as conn:
        conn.executescript(
            """
            CREATE TABLE mood_tags (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL
            );

            CREATE TABLE daily_records (
                id INTEGER PRIMARY KEY,
                date TEXT NOT NULL,
                title TEXT,
                mood_primary_id INTEGER,
                current_state TEXT,
                thoughts TEXT,
                focus_areas TEXT,
                tags TEXT,
                word_count INTEGER
            );
            """
        )
        conn.execute("INSERT INTO mood_tags (id, name) VALUES (1, 'calm')")
        conn.execute(
            """
            INSERT INTO daily_records (
                id, date, title, mood_primary_id, current_state, thoughts, focus_areas, tags, word_count
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                1,
                "2026-03-08",
                "Search-first homepage",
                1,
                "focused",
                "Refining the self interface into one strong entry point.",
                "memory, interface",
                "design,search",
                184,
            ),
        )


def _seed_preferences_db(path: Path) -> None:
    with sqlite3.connect(path) as conn:
        conn.executescript(
            """
            CREATE TABLE preference_items (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                is_positive INTEGER NOT NULL,
                intensity INTEGER NOT NULL,
                tags TEXT,
                notes TEXT,
                last_updated TEXT,
                updated_at TEXT,
                is_current INTEGER NOT NULL
            );

            CREATE TABLE website_preferences (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                category TEXT,
                usage_frequency TEXT,
                intensity INTEGER NOT NULL,
                updated_at TEXT,
                is_current INTEGER NOT NULL
            );
            """
        )
        conn.execute(
            """
            INSERT INTO preference_items (
                id, name, is_positive, intensity, tags, notes, last_updated, updated_at, is_current
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                1,
                "structured solitude",
                1,
                8,
                "focus,deep-work",
                "Prefers quiet systems with a single clear action.",
                "2026-03-08",
                "2026-03-08",
                1,
            ),
        )
        conn.execute(
            """
            INSERT INTO website_preferences (
                id, name, category, usage_frequency, intensity, updated_at, is_current
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (1, "Benself", "personal", "daily", 9, "2026-03-08", 1),
        )


def _seed_health_db(path: Path) -> None:
    with sqlite3.connect(path) as conn:
        conn.executescript(
            """
            CREATE TABLE workout_types (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL
            );

            CREATE TABLE workouts (
                id INTEGER PRIMARY KEY,
                workout_type_id INTEGER,
                start_time TEXT NOT NULL,
                duration_minutes INTEGER NOT NULL,
                intensity INTEGER NOT NULL,
                distance_km REAL,
                post_workout_mood TEXT,
                notes TEXT
            );

            CREATE TABLE body_metrics (
                id INTEGER PRIMARY KEY,
                recorded_at TEXT NOT NULL,
                weight REAL,
                bmi REAL,
                body_fat_percentage REAL,
                resting_heart_rate INTEGER
            );
            """
        )
        conn.execute("INSERT INTO workout_types (id, name) VALUES (1, 'walk')")
        conn.execute(
            """
            INSERT INTO workouts (
                id, workout_type_id, start_time, duration_minutes, intensity, distance_km, post_workout_mood, notes
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (1, 1, "2026-03-07T08:00:00", 42, 3, 3.8, "clear", "Morning reset"),
        )
        conn.execute(
            """
            INSERT INTO body_metrics (
                id, recorded_at, weight, bmi, body_fat_percentage, resting_heart_rate
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            (1, "2026-03-08T07:30:00", 68.2, 22.4, 16.8, 58),
        )


def _seed_finance_db(path: Path) -> None:
    with sqlite3.connect(path) as conn:
        conn.executescript(
            """
            CREATE TABLE transactions (
                id INTEGER PRIMARY KEY,
                type TEXT NOT NULL,
                amount REAL NOT NULL,
                transaction_date TEXT NOT NULL,
                description TEXT,
                merchant TEXT,
                notes TEXT
            );

            CREATE TABLE budgets (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                amount REAL NOT NULL,
                period TEXT NOT NULL,
                start_date TEXT NOT NULL,
                end_date TEXT,
                is_active INTEGER NOT NULL
            );
            """
        )
        conn.execute(
            """
            INSERT INTO transactions (
                id, type, amount, transaction_date, description, merchant, notes
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (1, "expense", 128.5, "2026-03-08", "Design books", "Bookshelf", "Reference material"),
        )
        conn.execute(
            """
            INSERT INTO budgets (
                id, name, amount, period, start_date, end_date, is_active
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (1, "Creative tools", 1200, "monthly", "2026-03-01", "2026-03-31", 1),
        )


@pytest.fixture()
def client(tmp_path: Path):
    db_path = tmp_path / "Benself-test.sqlite"
    journals_db = tmp_path / "journals.db"
    preferences_db = tmp_path / "preferences.db"
    health_db = tmp_path / "health.db"
    finance_db = tmp_path / "finance.db"
    _seed_journals_db(journals_db)
    _seed_preferences_db(preferences_db)
    _seed_health_db(health_db)
    _seed_finance_db(finance_db)

    os.environ["DATABASE_URL"] = f"sqlite:///{db_path}"
    os.environ["JOURNALS_DATABASE_PATH"] = str(journals_db)
    os.environ["PREFERENCES_DATABASE_PATH"] = str(preferences_db)
    os.environ["HEALTH_DATABASE_PATH"] = str(health_db)
    os.environ["FINANCE_DATABASE_PATH"] = str(finance_db)
    os.environ["GRAPHITI_ENABLED"] = "false"
    os.environ["GRAPHITI_KUZU_DB_PATH"] = str(tmp_path / "graphiti.kuzu")
    os.environ["APP_ENV"] = "test"
    os.environ["SECRET_KEY"] = "test-secret-key"
    os.environ["SSO_SECRET"] = "test-sso-secret"

    import benself_api.core.config as config_module

    config_module.get_settings.cache_clear()
    _run_migrations(os.environ["DATABASE_URL"])

    import benself_api.db.session as session_module

    session_module = importlib.reload(session_module)

    import benself_api.main as main_module

    main_module = importlib.reload(main_module)

    with TestClient(main_module.create_app()) as test_client:
        yield test_client

    config_module.get_settings.cache_clear()
