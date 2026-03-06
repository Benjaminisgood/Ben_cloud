from __future__ import annotations

from typing import Any

from fastapi import Request
from fastapi.responses import RedirectResponse

from benlab_api.models import Member


def login_redirect(request: Request):
    next_path = request.url.path
    if request.url.query:
        next_path = f"{next_path}?{request.url.query}"
    return RedirectResponse(url=f"{request.url_for('login')}?next={next_path}", status_code=303)


def with_common_query(context: dict[str, Any], request: Request) -> dict[str, Any]:
    context["query"] = request.query_params
    return context


def can_view_profile(current_user: Member | None, target: Member) -> bool:
    return current_user is not None and (current_user.id == target.id or current_user.id in {m.id for m in target.followers})
