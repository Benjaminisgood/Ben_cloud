from __future__ import annotations

from datetime import datetime, timezone

from fastapi import Request
from fastapi.templating import Jinja2Templates

from benlab_api.core.config import get_settings
from benlab_api.web.flash import pop_flashed_messages


templates = Jinja2Templates(directory=str(get_settings().TEMPLATES_DIR))


def _china_time(value: datetime | None, fmt: str = "%Y-%m-%d %H:%M") -> str:
    if not value:
        return ""
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).strftime(fmt)


templates.env.filters["china_time"] = _china_time


def _make_url_for(request: Request):
    def _url_for(endpoint: str, **params):
        if endpoint == "static":
            filename = params.pop("filename", "")
            return str(request.url_for("static", path=filename))
        return str(request.url_for(endpoint, **params))

    return _url_for


def render_template(
    request: Request,
    template_name: str,
    context: dict | None = None,
    current_user=None,
):
    payload = dict(context or {})

    def _flashes(with_categories=False):
        return pop_flashed_messages(request, with_categories=with_categories)

    payload.update(
        {
            "request": request,
            "url_for": _make_url_for(request),
            "current_user": current_user,
            "get_flashed_messages": _flashes,
            "direct_upload_config": {"enabled": False, "field_suffix": "_remote_keys"},
            "next_url": request.query_params.get("next", ""),
        }
    )
    return templates.TemplateResponse(request, template_name, payload)
