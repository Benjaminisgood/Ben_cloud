from __future__ import annotations

import logging
from pathlib import Path

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker

from .base import Base
from ..core.config import get_settings

logger = logging.getLogger(__name__)


def _make_engine():
    settings = get_settings()
    db_url = settings.DATABASE_URL
    if db_url.startswith("sqlite:///"):
        path = Path(db_url[len("sqlite:///") :])
        path.parent.mkdir(parents=True, exist_ok=True)
    connect_args = {"check_same_thread": False} if "sqlite" in db_url else {}
    return create_engine(db_url, connect_args=connect_args)


engine = _make_engine()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def create_all_tables() -> None:
    from ..models import Base as ModelsBase  # noqa: F401 - model registration side effect

    ModelsBase.metadata.create_all(bind=engine)
    _ensure_schema_shape()


def seed_admin() -> None:
    from ..models import User

    settings = get_settings()
    username = (settings.ADMIN_USERNAME or "").strip()
    password = settings.ADMIN_PASSWORD
    if not username or not password:
        return
    if "user" not in inspect(engine).get_table_names():
        return
    with SessionLocal() as db:
        existing = db.query(User).filter_by(username=username).first()
        if existing:
            if existing.role != "admin":
                existing.role = "admin"
                db.commit()
            return
        admin = User(username=username, role="admin", is_active=True)
        admin.set_password(password)
        db.add(admin)
        db.commit()


def _ensure_schema_shape() -> None:
    """Add missing columns from previous schema versions."""
    from ..models import AppSetting, Content, GeneratedAsset, Record  # noqa: F401

    inspector = inspect(engine)
    tables = set(inspector.get_table_names())

    def _add_col_if_missing(table: str, col: str, ddl: str) -> None:
        if table not in tables:
            return
        existing = {c["name"] for c in inspector.get_columns(table)}
        if col not in existing:
            with engine.begin() as conn:
                conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {ddl}"))

    _add_col_if_missing("generated_asset", "visibility", "visibility VARCHAR(16) NOT NULL DEFAULT 'private'")
    _add_col_if_missing("generated_asset", "status", "status VARCHAR(16) NOT NULL DEFAULT 'ready'")
    _add_col_if_missing("generated_asset", "is_daily_digest", "is_daily_digest BOOLEAN NOT NULL DEFAULT 0")
    _add_col_if_missing("generated_asset", "source_day", "source_day DATE")
    _add_col_if_missing("generated_asset", "file_type", "file_type VARCHAR(16) NOT NULL DEFAULT 'file'")
    _add_col_if_missing("content", "file_type", "file_type VARCHAR(16) NOT NULL DEFAULT 'file'")
