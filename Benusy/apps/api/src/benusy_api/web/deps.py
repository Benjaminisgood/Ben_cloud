from __future__ import annotations

from fastapi import Depends, Request
from sqlmodel import Session

from benusy_api.db.database import get_session
from benusy_api.models import User


def get_db():
    yield from get_session()


def get_session_user(request: Request, db: Session = Depends(get_db)) -> User | None:
    user_id = request.session.get("user_id")
    if not user_id:
        return None
    user = db.get(User, int(user_id))
    if not user or not user.is_active:
        request.session.clear()
        return None
    return user


def login_session(request: Request, user: User) -> None:
    request.session["user_id"] = user.id
    request.session["username"] = user.username
    request.session["role"] = user.role.value


def logout_session(request: Request) -> None:
    request.session.clear()
