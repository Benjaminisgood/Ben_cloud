
from __future__ import annotations

from fastapi import Depends, HTTPException, Request
from sqlalchemy.orm import Session

from benfinance_api.db.session import get_db as get_db_session


def get_db() -> Session:
    return next(get_db_session())


def require_user(request: Request) -> dict[str, str]:
    user = request.session.get("user")
    if not user:
        raise HTTPException(status_code=401, detail="auth_required")
    return user


def require_admin(request: Request) -> dict[str, str]:
    user = require_user(request)
    if str(user.get("role", "user")) != "admin":
        raise HTTPException(status_code=403, detail="admin_required")
    return user
