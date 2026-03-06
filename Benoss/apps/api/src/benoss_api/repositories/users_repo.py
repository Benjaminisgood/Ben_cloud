from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import User


def get_user_by_username(db: Session, *, username: str) -> User | None:
    return db.scalar(select(User).where(User.username == username))


def get_active_user_by_username(db: Session, *, username: str) -> User | None:
    return db.scalar(select(User).where(User.username == username, User.is_active.is_(True)))

