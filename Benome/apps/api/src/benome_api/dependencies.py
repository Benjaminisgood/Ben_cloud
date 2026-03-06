from __future__ import annotations

from fastapi import Depends, Header, HTTPException, Request
from sqlalchemy.orm import Session

from .db.session import get_db
from .models import User
from .repositories.users_repo import get_user_by_id


def get_current_user(
    request: Request,
    x_user_id: str | None = Header(default=None, alias="X-User-Id"),
    db: Session = Depends(get_db),
) -> User:
    user_id_value: str | None = None
    if x_user_id is not None:
        if not x_user_id.isdigit():
            raise HTTPException(status_code=401, detail="invalid X-User-Id")
        user_id_value = x_user_id
    else:
        session_user_id = request.session.get("user_id")
        if session_user_id is not None:
            user_id_value = str(session_user_id)
            if not user_id_value.isdigit():
                raise HTTPException(status_code=401, detail="invalid session user_id")

    if not user_id_value:
        raise HTTPException(status_code=401, detail="authentication required")

    user = get_user_by_id(db, user_id=int(user_id_value))
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="user not found or inactive")
    return user


def get_current_admin(user: User = Depends(get_current_user)) -> User:
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="admin only")
    return user


def get_current_customer(user: User = Depends(get_current_user)) -> User:
    if user.role != "customer":
        raise HTTPException(status_code=403, detail="customer only")
    return user


__all__ = [
    "get_db",
    "get_current_user",
    "get_current_admin",
    "get_current_customer",
]
