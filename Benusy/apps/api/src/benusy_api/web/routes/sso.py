"""Benbot SSO callback endpoint for Benusy."""
from __future__ import annotations

import secrets

from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse
from sqlmodel import Session, select

from benusy_api.core.config import get_settings
from benusy_api.core.security import get_password_hash
from benusy_api.models import ReviewStatus, Role, User
from benusy_api.services.sso import verify_sso_token

from ..deps import get_db, login_session

router = APIRouter(tags=["sso"])
settings = get_settings()


def _normalize_email(username: str) -> str:
    text = username.strip()
    return text if "@" in text else f"{text}@benbot.local"


def _map_role(role: str) -> Role:
    return Role.admin if role == "admin" else Role.blogger


def _find_or_create_user(db: Session, username: str, role: Role) -> User:
    email = _normalize_email(username)
    user = db.exec(select(User).where(User.username == username)).first()
    if user is None:
        user = db.exec(select(User).where(User.email == email)).first()

    if user is None:
        user = User(
            email=email,
            username=username,
            display_name=username,
            real_name=username,
            hashed_password=get_password_hash(secrets.token_urlsafe(24)),
            role=role,
            review_status=ReviewStatus.approved,
            is_active=True,
            tags="sso",
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        return user

    dirty = False
    if user.role != role:
        user.role = role
        dirty = True
    if user.review_status != ReviewStatus.approved:
        user.review_status = ReviewStatus.approved
        dirty = True
    if not user.is_active:
        user.is_active = True
        dirty = True
    if dirty:
        db.add(user)
        db.commit()
        db.refresh(user)
    return user


@router.get("/auth/sso")
def sso_callback(token: str, request: Request, db: Session = Depends(get_db)):
    payload = verify_sso_token(settings.SSO_SECRET, token)
    if not payload:
        return RedirectResponse("/login?sso=invalid", status_code=302)

    username = str(payload.get("u", "")).strip()
    if not username:
        return RedirectResponse("/login?sso=invalid", status_code=302)

    role = _map_role(str(payload.get("r", "blogger")))
    user = _find_or_create_user(db, username=username, role=role)
    if not user.is_active:
        return RedirectResponse("/login?sso=inactive", status_code=302)

    login_session(request, user)
    # Redirect based on role: admin → admin dashboard, blogger → user dashboard
    if user.role == Role.admin:
        return RedirectResponse("/admin/dashboard", status_code=302)
    else:
        return RedirectResponse("/dashboard", status_code=302)
