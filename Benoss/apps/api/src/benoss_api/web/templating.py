from __future__ import annotations

from pathlib import Path

from fastapi import Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from ..core.config import get_settings

templates = Jinja2Templates(directory=str(get_settings().WEB_TEMPLATES_DIR))


def _asset_version() -> str:
    settings = get_settings()
    static_dir = Path(settings.WEB_STATIC_DIR)
    tracked = [
        static_dir / "css" / "main.css",
        static_dir / "js" / "site.js",
        static_dir / "js" / "admin.js",
    ]
    mtimes = [int(path.stat().st_mtime) for path in tracked if path.exists()]
    if not mtimes:
        return str(settings.APP_VERSION)
    return str(max(mtimes))


def render_template(request: Request, name: str, context: dict) -> HTMLResponse:
    context.setdefault("request", request)
    context.setdefault("flash_messages", [])
    context.setdefault("asset_version", _asset_version())
    return templates.TemplateResponse(name, context)
