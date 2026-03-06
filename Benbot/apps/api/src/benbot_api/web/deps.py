from __future__ import annotations

import hmac
from typing import Protocol

from fastapi import Depends, HTTPException, Request, status
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from ..core.config import get_settings
from ..db.session import get_db
from ..models import User
from ..repositories import get_user_by_id
from ..schemas.web import ApiTokenUserDTO, SessionUserDTO
from ..services.metrics import inc_counter

AdminPrincipalDTO = SessionUserDTO | ApiTokenUserDTO


def _to_session_user_dto(user: User) -> SessionUserDTO:
    return SessionUserDTO(
        id=user.id,
        username=user.username,
        role=user.role,
        is_active=user.is_active,
    )


def get_session_user(request: Request, db: Session = Depends(get_db)) -> SessionUserDTO | None:
    user_id = request.session.get("user_id")
    if not user_id:
        return None
    user = get_user_by_id(db, user_id)
    if not user or not user.is_active:
        request.session.clear()
        return None
    return _to_session_user_dto(user)


def get_api_token_user(request: Request, db: Session = Depends(get_db)) -> ApiTokenUserDTO | None:
    """
    Authenticate using API token from X-API-Token header.
    Returns admin user if token matches NANOBOT_API_TOKEN.
    """
    settings = get_settings()
    token = request.headers.get("X-API-Token", "")
    expected = settings.NANOBOT_API_TOKEN.strip()
    if not token or not expected:
        return None

    if not hmac.compare_digest(token, expected):
        return None

    allowed_ips = settings.nanobot_allowed_ips_set
    if allowed_ips:
        remote_ip = (request.client.host if request.client else "").strip()
        if remote_ip not in allowed_ips:
            return None

    inc_counter("benbot_api_token_auth_total")
    return ApiTokenUserDTO(scopes=settings.nanobot_api_scope_set)


def require_session_user_or_redirect(
    request: Request,
    db: Session = Depends(get_db),
) -> SessionUserDTO | RedirectResponse:
    user = get_session_user(request, db)
    if user:
        return user
    return RedirectResponse(f"/login?next={request.url.path}", status_code=302)


def require_guest_or_redirect_home(
    request: Request,
    db: Session = Depends(get_db),
) -> RedirectResponse | None:
    if get_session_user(request, db):
        return RedirectResponse("/", status_code=302)
    return None


def require_session_user_or_401(
    request: Request,
    db: Session = Depends(get_db),
    *,
    detail: str = "unauthorized",
) -> SessionUserDTO:
    user = get_session_user(request, db)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=detail)
    return user


def require_admin_session_user_or_403(
    request: Request,
    db: Session = Depends(get_db),
) -> SessionUserDTO:
    user = require_session_user_or_401(request, db)
    if user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="forbidden")
    return user


def require_admin_principal_or_401(
    request: Request,
    db: Session = Depends(get_db),
    *,
    required_scope: str | None = None,
) -> AdminPrincipalDTO:
    user = get_session_user(request, db)
    if user:
        if user.role != "admin":
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="forbidden")
        return user

    token_user = get_api_token_user(request, db)
    if token_user:
        if required_scope and not token_user.has_scope(required_scope):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="insufficient_scope")
        return token_user

    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="unauthorized")


class _SessionPrincipal(Protocol):
    id: int
    username: str
    role: str


def login_session(request: Request, user: _SessionPrincipal) -> None:
    request.session["user_id"] = user.id
    request.session["username"] = user.username
    request.session["role"] = user.role


def logout_session(request: Request) -> None:
    request.session.clear()
