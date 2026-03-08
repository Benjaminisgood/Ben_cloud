
from __future__ import annotations

from fastapi import Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from benfinance_api.core.config import get_settings

templates = Jinja2Templates(directory=str(get_settings().TEMPLATES_DIR))


def render_template(
    request: Request,
    template_name: str,
    context: dict | None = None,
    *,
    status_code: int = 200,
) -> HTMLResponse:
    payload = {"request": request}
    if context:
        payload.update(context)
    return templates.TemplateResponse(template_name, payload, status_code=status_code)
