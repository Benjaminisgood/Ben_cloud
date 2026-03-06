from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import User


def get_user_by_id(db: Session, *, user_id: int) -> User | None:
    return db.scalar(select(User).where(User.id == user_id))


def get_user_by_username(db: Session, *, username: str) -> User | None:
    return db.scalar(select(User).where(User.username == username))


def list_users(db: Session) -> list[User]:
    stmt = select(User).order_by(User.created_at.desc(), User.id.desc())
    return list(db.scalars(stmt).all())


def create_user(
    db: Session,
    *,
    username: str,
    password: str,
    role: str = "customer",
    full_name: str = "",
    phone: str = "",
) -> User:
    user = User(username=username, role=role, is_active=True, full_name=full_name, phone=phone)
    user.set_password(password)
    db.add(user)
    db.flush()
    return user
