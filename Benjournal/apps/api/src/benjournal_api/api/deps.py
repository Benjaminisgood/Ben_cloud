
from __future__ import annotations

from fastapi import HTTPException, Request


def require_user(request: Request) -> dict[str, str]:
    user = request.session.get("user")
    if not user:
        raise HTTPException(status_code=401, detail="auth_required")
    return user
