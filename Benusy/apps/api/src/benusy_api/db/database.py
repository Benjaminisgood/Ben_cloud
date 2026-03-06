from __future__ import annotations

from typing import Iterator

from sqlmodel import SQLModel, Session, create_engine

from benusy_api.core.config import get_settings

settings = get_settings()
connect_args = {"check_same_thread": False} if settings.DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(settings.DATABASE_URL, echo=settings.DEBUG, connect_args=connect_args)


def create_all_tables() -> None:
    # Import models to populate SQLModel metadata before create_all.
    import benusy_api.models  # noqa: F401

    SQLModel.metadata.create_all(engine)


def create_db_and_tables() -> None:
    # Backward-compat alias for legacy modules/scripts.
    create_all_tables()


def drop_db_and_tables() -> None:
    SQLModel.metadata.drop_all(engine)


def rebuild_db() -> None:
    drop_db_and_tables()
    create_all_tables()


def get_session() -> Iterator[Session]:
    with Session(engine) as session:
        yield session
