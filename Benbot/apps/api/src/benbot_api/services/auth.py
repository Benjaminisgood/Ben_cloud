from __future__ import annotations

from sqlalchemy.orm import Session

from ..models import User
from ..repositories import create_user as repo_create_user
from ..repositories import get_user_by_username as repo_get_user_by_username


def authenticate_user(db: Session, *, username: str, password: str) -> User | None:
    user = repo_get_user_by_username(db, username, active_only=True)
    if not user or not user.check_password(password):
        return None
    return user


def get_user_by_username(db: Session, *, username: str) -> User | None:
    return repo_get_user_by_username(db, username)


def create_user(db: Session, *, username: str, password: str, role: str = "user") -> User:
    return repo_create_user(db, username=username, password=password, role=role, is_active=True)


def validate_login_input(username: str, password: str) -> str | None:
    if not username:
        return "用户名不能为空"
    if not password:
        return "密码不能为空"
    return None


def validate_register_input(username: str, password: str, confirm_password: str) -> str | None:
    if not username or len(username) < 3 or len(username) > 20:
        return "用户名长度必须在 3-20 个字符之间"
    if not username.replace("_", "").isalnum():
        return "用户名只能包含字母、数字和下划线"
    if not password or len(password) < 6:
        return "密码长度至少为 6 位"
    if password != confirm_password:
        return "两次输入的密码不一致"
    return None
