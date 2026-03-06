from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from ...core.auth import get_session_user, unauthorized_html
from ...core.config import ROOT_DIR

router = APIRouter(tags=["pages"])


@router.get("/", response_class=HTMLResponse)
async def index(request: Request):
    if get_session_user(request) is None:
        return HTMLResponse(content=unauthorized_html(), status_code=401)

    html_path = ROOT_DIR / "templates" / "editor.html"
    return HTMLResponse(content=html_path.read_text(encoding="utf-8"))
