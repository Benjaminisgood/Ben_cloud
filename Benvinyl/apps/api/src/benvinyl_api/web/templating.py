from __future__ import annotations

from fastapi import Request
from fastapi.templating import Jinja2Templates

from ..core.config import get_settings

templates = Jinja2Templates(directory=str(get_settings().TEMPLATES_DIR))


def render_template(request: Request, template_name: str, context: dict):
    return templates.TemplateResponse(request, template_name, context)
