
from __future__ import annotations

from collections.abc import Generator

from fastapi import HTTPException, Request
from sqlalchemy.orm import Session

from benphoto_api.db.session import get_db as get_db_session


def get_db() -> Generator[Session, None, None]:
    yield from get_db_session()


def require_user(request: Request) -> dict[str, str]:
    user = request.session.get("user")
    if not isinstance(user, dict):
        raise HTTPException(status_code=401, detail="auth_required")
    return {"username": str(user.get("username", "")), "role": str(user.get("role", "user"))}
