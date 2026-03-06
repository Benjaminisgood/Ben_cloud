"""Benbot SSO callback endpoint for Benlab.

When Benbot redirects a user here with a signed token, we validate it,
find or create the local member, and create a session.
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

from benlab_api.db.session import get_db
from benlab_api.models import Member
from benlab_api.services.security import hash_password

router = APIRouter(tags=["sso"])


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


def _find_or_create_member(db: Session, username: str) -> Member:
    from sqlalchemy import select

    member = db.scalar(select(Member).where(Member.username == username))
    if member is None:
        member = Member(
            username=username,
            name=username,  # use username as display name for SSO users
            password_hash=hash_password(os.urandom(24).hex()),  # unusable random password
        )
        db.add(member)
        db.commit()
        db.refresh(member)
    return member


@router.get("/auth/sso")
def sso_callback(token: str, request: Request, db: Session = Depends(get_db)):
    """Validate Benbot SSO token and log user into Benlab."""
    payload = _verify_token(token)
    if not payload:
        return RedirectResponse("/login?sso=invalid", status_code=302)

    username = payload.get("u", "")
    if not username:
        return RedirectResponse("/login?sso=invalid", status_code=302)

    member = _find_or_create_member(db, username)
    request.session["user_id"] = member.id
    return RedirectResponse("/", status_code=302)
