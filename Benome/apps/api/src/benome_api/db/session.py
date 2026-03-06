from __future__ import annotations

from pathlib import Path
from typing import Iterator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from ..core.config import get_settings
from ..models import User


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


def get_db() -> Iterator[Session]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def create_all_tables() -> None:
    from ..models import Booking, BookingNightLock, Property, User  # noqa: F401
    from .base import Base

    Base.metadata.create_all(bind=engine)


def seed_admin() -> None:
    settings = get_settings()
    username = (settings.ADMIN_USERNAME or "").strip()
    password = settings.ADMIN_PASSWORD or ""
    if not username or not password:
        return

    with SessionLocal() as db:
        existing = db.query(User).filter(User.username == username).first()
        if existing:
            if existing.role != "admin":
                existing.role = "admin"
                db.commit()
            return

        admin = User(
            username=username,
            role="admin",
            is_active=True,
            full_name="系统管理员",
            phone="",
        )
        admin.set_password(password)
        db.add(admin)
        db.commit()
