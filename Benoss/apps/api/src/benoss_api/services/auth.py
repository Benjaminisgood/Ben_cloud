from __future__ import annotations

from sqlalchemy.orm import Session

from ..models import User
from ..repositories.users_repo import get_active_user_by_username, get_user_by_username


def authenticate_user(db: Session, *, username: str, password: str) -> User | None:
    user = get_active_user_by_username(db, username=username)
    if not user or not user.check_password(password):
        return None
    return user


def validate_registration_input(username: str, password: str, password_confirm: str) -> str | None:
    if not username:
        return "用户名不能为空"
    if not (3 <= len(username) <= 40):
        return "用户名长度需在 3-40 之间"
    if password != password_confirm:
        return "两次输入的密码不一致"
    if len(password) < 6:
        return "密码至少 6 位"
    return None


def username_exists(db: Session, *, username: str) -> bool:
    return get_user_by_username(db, username=username) is not None


def create_user(db: Session, *, username: str, password: str, role: str = "user") -> User:
    user = User(username=username, role=role, is_active=True)
    user.set_password(password)
    db.add(user)
    db.commit()
    return user

