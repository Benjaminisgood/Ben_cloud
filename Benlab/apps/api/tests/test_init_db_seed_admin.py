from __future__ import annotations

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from benlab_api.core.config import get_settings
from benlab_api.db.base import Base
from benlab_api.db.init_db import seed_admin
from benlab_api.models import Member
from benlab_api.services.security import verify_password


def _make_db() -> Session:
    engine = create_engine(
        "sqlite+pysqlite://",
        future=True,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    return sessionmaker(autocommit=False, autoflush=False, bind=engine, expire_on_commit=False)()


def test_seed_admin_reads_env_credentials(monkeypatch) -> None:
    get_settings.cache_clear()
    monkeypatch.setenv("ADMIN_USERNAME", "seed-root")
    monkeypatch.setenv("ADMIN_PASSWORD", "seed-pass")

    db = _make_db()
    try:
        seed_admin(db)
        admin = db.scalar(select(Member).where(Member.username == "seed-root"))
        assert admin is not None
        assert verify_password("seed-pass", admin.password_hash)
    finally:
        db.close()
        get_settings.cache_clear()


def test_seed_admin_skips_when_credentials_empty(monkeypatch) -> None:
    get_settings.cache_clear()
    monkeypatch.setenv("ADMIN_USERNAME", "")
    monkeypatch.setenv("ADMIN_PASSWORD", "")

    db = _make_db()
    try:
        seed_admin(db)
        assert db.scalar(select(Member).where(Member.username == "admin")) is None
    finally:
        db.close()
        get_settings.cache_clear()
