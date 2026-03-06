from __future__ import annotations

from fastapi import Depends, HTTPException, Request

from ..models import User
from ..web.deps import get_session_user


def require_api_user(
    request: Request,
    user: User | None = Depends(get_session_user),
) -> User:
    if not user:
        raise HTTPException(status_code=401, detail="login required")
    return user


def require_api_admin(user: User = Depends(require_api_user)) -> User:
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="forbidden")
    return user
