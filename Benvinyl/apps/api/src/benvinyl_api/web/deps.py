from __future__ import annotations

from fastapi import Request


def get_session_user(request: Request) -> dict[str, str] | None:
    user = request.session.get("user")
    if not isinstance(user, dict):
        return None
    return {"username": str(user.get("username", "")), "role": str(user.get("role", "user"))}


def login_session(request: Request, *, username: str, role: str) -> None:
    request.session["user"] = {"username": username, "role": role}


def logout_session(request: Request) -> None:
    request.session.clear()
