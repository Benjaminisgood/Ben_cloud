from __future__ import annotations

from sqlalchemy.orm import Session

from ..models.user import User


def get_user_by_id(db: Session, user_id: int) -> User | None:
    return db.get(User, user_id)


def get_user_by_username(db: Session, username: str, *, active_only: bool = False) -> User | None:
    query = db.query(User).filter_by(username=username)
    if active_only:
        query = query.filter_by(is_active=True)
    return query.first()


def create_user(
    db: Session,
    *,
    username: str,
    password: str,
    role: str = "user",
    is_active: bool = True,
) -> User:
    user = User(username=username, role=role, is_active=is_active)
    user.set_password(password)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def update_user_role(db: Session, user: User, role: str) -> User:
    user.role = role
    db.commit()
    db.refresh(user)
    return user


def has_active_admin(db: Session) -> bool:
    return db.query(User).filter_by(role="admin", is_active=True).first() is not None


def count_active_admins(db: Session) -> int:
    return db.query(User).filter_by(role="admin", is_active=True).count()
