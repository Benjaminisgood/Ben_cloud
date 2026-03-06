"""Benome API application entry point."""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

from .api import api_router
from .core.config import get_settings
from .db.migrations import ensure_migration_state
from .db.session import create_all_tables, seed_admin
from .web import web_router

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s - %(message)s")
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI):
    settings = get_settings()
    settings.ensure_data_dirs()
    if settings.DB_BOOTSTRAP_CREATE_ALL:
        create_all_tables()
    ensure_migration_state()
    seed_admin()
    logger.info("Application startup complete")
    yield
    logger.info("Application shutdown complete")


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
        session_cookie=settings.SESSION_COOKIE_NAME,
        max_age=settings.REMEMBER_DAYS * 24 * 3600,
        same_site=settings.SESSION_COOKIE_SAMESITE,
        https_only=settings.SESSION_COOKIE_SECURE,
    )

    if settings.WEB_STATIC_DIR.exists():
        app.mount("/static", StaticFiles(directory=str(settings.WEB_STATIC_DIR)), name="static")
    else:
        logger.warning("Web static directory not found: %s", settings.WEB_STATIC_DIR)

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
        "benome_api.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.APP_ENV == "development",
    )


if __name__ == "__main__":
    run()
