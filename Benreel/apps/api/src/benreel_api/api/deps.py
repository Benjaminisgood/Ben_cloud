from __future__ import annotations

from fastapi import HTTPException, Request, status


def get_session_user(request: Request) -> dict[str, str] | None:
    user = request.session.get("user")
    if not isinstance(user, dict):
        return None
    return {"username": str(user.get("username", "")).strip(), "role": str(user.get("role", "user")).strip() or "user"}


def require_admin(request: Request) -> dict[str, str]:
    user = get_session_user(request)
    if not user or not user["username"]:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="auth_required")
    if user["role"] != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="admin_required")
    return user
