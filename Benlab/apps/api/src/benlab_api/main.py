"""Benlab FastAPI standardized entrypoint."""
from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

from .api import api_router
from .core.config import get_settings
from .web import web_router

from benlab_api.db.init_db import init_db  # noqa: E402
from benlab_api.web.deps import AnonymousUser  # noqa: E402
from benlab_api.web.templating import render_template  # noqa: E402
from benlab_api.web.viewmodels import base_template_context  # noqa: E402


@asynccontextmanager
async def lifespan(_: FastAPI):
    get_settings().ensure_data_dirs()
    init_db()
    yield


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
    )
    app.add_middleware(
        SessionMiddleware,
        secret_key=settings.SECRET_KEY,
        max_age=settings.REMEMBER_DAYS * 24 * 3600,
        same_site=settings.SESSION_COOKIE_SAMESITE,
        https_only=settings.SESSION_COOKIE_SECURE,
    )

    static_dir = settings.STATIC_DIR
    if not static_dir.is_absolute():
        static_dir = Path.cwd() / static_dir
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

    @app.exception_handler(403)
    async def forbidden_handler(request: Request, exc):  # noqa: ARG001
        current_user = getattr(request.state, "current_user", None) or AnonymousUser()
        context = base_template_context()
        context.update({"back_url": "/", "description": "该资源仅向负责人开放，请联系负责人授予权限。"})
        return render_template(request, "error_403.html", context, current_user=current_user)

    app.include_router(web_router)
    app.include_router(api_router)

    @app.get("/health", tags=["health"])
    def health() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()


def run() -> None:
    import uvicorn

    settings = get_settings()
    uvicorn.run(
        "benlab_api.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.APP_ENV == "development",
    )


if __name__ == "__main__":
    run()
