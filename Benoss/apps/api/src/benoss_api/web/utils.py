from __future__ import annotations

from fastapi import Request
from fastapi.responses import RedirectResponse


def login_redirect(request: Request, *, next_path: str | None = None) -> RedirectResponse:
    path = next_path if next_path is not None else request.url.path
    return RedirectResponse(f"/login?next={path}", status_code=302)
