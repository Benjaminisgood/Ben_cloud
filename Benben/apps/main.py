from __future__ import annotations

import time
from uuid import uuid4

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

from .api.router import router as api_router
from .core.config import ROOT_DIR, get_settings
from .web.router import router as web_router

settings = get_settings()

app = FastAPI(title=f"{settings.app_name} Markdown Editor")
app.add_middleware(
    SessionMiddleware,
    secret_key=settings.session_secret_key,
    max_age=settings.session_max_age_seconds,
    same_site="lax",
    https_only=settings.session_cookie_secure,
)

app.include_router(api_router)
app.include_router(web_router)

static_path = ROOT_DIR / "static"
if static_path.exists():
    app.mount("/static", StaticFiles(directory=static_path), name="static")


@app.middleware("http")
async def request_trace_middleware(request, call_next):
    request_id = (request.headers.get("X-Request-ID") or "").strip() or uuid4().hex
    request.state.request_id = request_id
    started_at = time.perf_counter()

    response = await call_next(request)
    duration_ms = (time.perf_counter() - started_at) * 1000
    response.headers["X-Request-ID"] = request_id
    response.headers["X-Process-Time-Ms"] = f"{duration_ms:.2f}"
    return response
