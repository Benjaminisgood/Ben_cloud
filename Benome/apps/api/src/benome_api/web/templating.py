from __future__ import annotations

from fastapi import Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from ..core.config import get_settings

templates = Jinja2Templates(directory=str(get_settings().WEB_TEMPLATES_DIR))


def render_template(request: Request, name: str, context: dict) -> HTMLResponse:
    context.setdefault("request", request)
    return templates.TemplateResponse(request, name, context)
