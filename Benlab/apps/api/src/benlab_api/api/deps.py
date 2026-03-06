from __future__ import annotations

from fastapi import Depends, HTTPException, Request

from ..models import Member
from ..services.admin_identity import is_admin_member
from ..web.deps import get_current_user


def require_api_user(
    request: Request,  # noqa: ARG001
    user: Member | None = Depends(get_current_user),
) -> Member:
    if not user:
        raise HTTPException(status_code=401, detail="login required")
    return user


def require_api_admin(user: Member = Depends(require_api_user)) -> Member:
    if not is_admin_member(user):
        raise HTTPException(status_code=403, detail="forbidden")
    return user
