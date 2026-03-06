from __future__ import annotations

from fastapi import Depends, Request
from sqlalchemy.orm import Session

from benlab_api.db.session import get_db
from benlab_api.models import Member


class AnonymousUser:
    id = None
    username = ""
    name = ""
    is_authenticated = False
    is_anonymous = True


def get_current_user(
    request: Request,
    db: Session = Depends(get_db),
) -> Member | None:
    if hasattr(request.state, "current_user_loaded"):
        return request.state.current_user
    user_id = request.session.get("user_id")
    user = db.get(Member, int(user_id)) if user_id else None
    request.state.current_user = user
    request.state.current_user_loaded = True
    return user


def get_current_user_or_anonymous(
    current_user: Member | None = Depends(get_current_user),
) -> Member | AnonymousUser:
    return current_user or AnonymousUser()
