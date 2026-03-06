"""Benbot SSO callback endpoint for Benoss.

When Benbot redirects a user here with a signed token, we validate it,
find or create the local user, and create a session.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import time

from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from ...db.session import get_db
from ...models import User
from ..deps import login_session

router = APIRouter(tags=["sso"])

_SSO_TOKEN_TTL = 60  # seconds, slightly longer than Benbot's 30s for clock skew


def _get_sso_secret() -> str:
    return os.environ.get("SSO_SECRET", "benbot-sso-secret-2025")


def _verify_token(token: str) -> dict | None:
    secret = _get_sso_secret()
    try:
        decoded = base64.urlsafe_b64decode(token.encode()).decode()
        dot_pos = decoded.rfind(".")
        if dot_pos == -1:
            return None
        data, sig = decoded[:dot_pos], decoded[dot_pos + 1:]
        expected = hmac.new(secret.encode(), data.encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(sig, expected):
            return None
        payload = json.loads(data)
        if payload.get("e", 0) < time.time():
            return None
        return payload
    except Exception:
        return None


def _find_or_create_user(db: Session, username: str, role: str) -> User:
    user = db.query(User).filter_by(username=username).first()
    if user is None:
        user = User(username=username, role=role, is_active=True)
        user.set_password(os.urandom(24).hex())  # random unusable password
        db.add(user)
        db.commit()
        db.refresh(user)
    elif user.role != role:
        user.role = role
        db.commit()
    return user


@router.get("/auth/sso")
def sso_callback(token: str, request: Request, db: Session = Depends(get_db)):
    """Validate Benbot SSO token and log user into Benoss."""
    payload = _verify_token(token)
    if not payload:
        return RedirectResponse("/login?sso=invalid", status_code=302)

    username = payload.get("u", "")
    role = payload.get("r", "user")
    if not username:
        return RedirectResponse("/login?sso=invalid", status_code=302)

    user = _find_or_create_user(db, username, role)
    if not user.is_active:
        return RedirectResponse("/login?sso=inactive", status_code=302)

    login_session(request, user)
    return RedirectResponse("/", status_code=302)
