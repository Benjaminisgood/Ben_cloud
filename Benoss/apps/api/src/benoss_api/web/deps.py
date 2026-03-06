from __future__ import annotations

from fastapi import Depends, Request
from sqlalchemy.orm import Session

from ..db.session import get_db
from ..models import User


def get_session_user(request: Request, db: Session = Depends(get_db)) -> User | None:
    """Return current User from session, or None if not authenticated."""
    user_id = request.session.get("user_id")
    if not user_id:
        return None
    user = db.get(User, user_id)
    if not user or not user.is_active:
        request.session.clear()
        return None
    return user


def login_session(request: Request, user: User) -> None:
    request.session["user_id"] = user.id
    request.session["username"] = user.username
    request.session["role"] = user.role


def logout_session(request: Request) -> None:
    request.session.clear()
