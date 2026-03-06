from __future__ import annotations

from fastapi import Request
from fastapi.templating import Jinja2Templates

from benusy_api.core.config import get_settings

settings = get_settings()
templates = Jinja2Templates(directory=str(settings.WEB_TEMPLATES_DIR))


def render_template(request: Request, template_name: str, context: dict | None = None):
    payload = {"request": request}
    if context:
        payload.update(context)
    return templates.TemplateResponse(template_name, payload)
