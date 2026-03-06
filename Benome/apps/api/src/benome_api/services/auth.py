from __future__ import annotations

from sqlalchemy.orm import Session

from ..models import User
from ..repositories.users_repo import create_user, get_user_by_username
from .errors import ServiceError


def validate_register_input(username: str, password: str) -> None:
    username = username.strip()
    if not username:
        raise ServiceError("username required", status_code=400)
    if len(username) < 3 or len(username) > 40:
        raise ServiceError("username length must be 3-40", status_code=400)
    if len(password) < 6:
        raise ServiceError("password must be at least 6 chars", status_code=400)


def register_customer(
    db: Session,
    *,
    username: str,
    password: str,
    full_name: str,
    phone: str,
) -> User:
    validate_register_input(username, password)
    if get_user_by_username(db, username=username):
        raise ServiceError("username already exists", status_code=409)

    user = create_user(
        db,
        username=username,
        password=password,
        role="customer",
        full_name=full_name,
        phone=phone,
    )
    db.commit()
    db.refresh(user)
    return user


def login(db: Session, *, username: str, password: str) -> User:
    user = get_user_by_username(db, username=username)
    if not user or not user.is_active or not user.check_password(password):
        raise ServiceError("invalid username or password", status_code=401)
    return user
