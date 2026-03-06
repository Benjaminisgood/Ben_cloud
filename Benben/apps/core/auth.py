from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
from typing import Any

from fastapi import HTTPException, Request

from .config import get_settings

_ALLOWED_ROLES = {"admin", "user"}


def _decode_base64url(raw: str) -> str:
    payload = raw.strip()
    if not payload:
        raise ValueError("empty token")

    padding = "=" * (-len(payload) % 4)
    return base64.urlsafe_b64decode((payload + padding).encode("utf-8")).decode("utf-8")


def validate_sso_token(token: str) -> dict[str, Any]:
    try:
        settings = get_settings()
        decoded = _decode_base64url(token)
        dot_pos = decoded.rfind(".")
        if dot_pos == -1:
            raise ValueError("invalid token format")

        data, signature = decoded[:dot_pos], decoded[dot_pos + 1 :]

        expected_signature = hmac.new(
            settings.sso_secret.encode("utf-8"),
            data.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()

        if not hmac.compare_digest(signature, expected_signature):
            raise ValueError("invalid token signature")

        payload = json.loads(data)
        username = str(payload.get("u") or "").strip()
        role = str(payload.get("r") or "").strip()
        exp = int(payload.get("e", 0))

        if not username or len(username) > 64:
            raise ValueError("invalid username")
        if role not in _ALLOWED_ROLES:
            raise ValueError("invalid role")
        if exp < int(time.time()):
            raise ValueError("token expired")

        return {
            "username": username,
            "role": role,
            "exp": exp,
        }
    except Exception as exc:
        raise HTTPException(status_code=401, detail="Invalid or expired token") from exc


def set_session_user(request: Request, *, username: str, role: str) -> None:
    request.session.clear()
    request.session["user"] = {
        "username": username,
        "role": role,
        "login_at": int(time.time()),
    }


def get_session_user(request: Request) -> dict[str, str] | None:
    raw_user = request.session.get("user")
    if not isinstance(raw_user, dict):
        return None

    username = str(raw_user.get("username") or "").strip()
    role = str(raw_user.get("role") or "").strip()
    if not username or role not in _ALLOWED_ROLES:
        request.session.clear()
        return None

    return {"username": username, "role": role}


def require_session_user(request: Request) -> dict[str, str]:
    user = get_session_user(request)
    if user is None:
        raise HTTPException(status_code=401, detail="unauthorized")
    return user


def unauthorized_html() -> str:
    return (
        "<html><head><meta charset='utf-8'><title>未授权</title></head>"
        "<body style='font-family: sans-serif; padding: 32px;'>"
        "<h2>未登录或会话已过期</h2>"
        "<p>请从 Benbot 门户重新进入 Benben。</p>"
        "</body></html>"
    )
