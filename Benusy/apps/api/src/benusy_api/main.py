"""Benusy API application entry point."""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from sqlmodel import Session, select
from starlette.middleware.sessions import SessionMiddleware

from benusy_api.api import api_router
from benusy_api.core.config import get_settings
from benusy_api.core.security import get_password_hash
from benusy_api.db.database import create_all_tables, engine
from benusy_api.db.migrations import ensure_migration_state
from benusy_api.models import PlatformMetricConfig, ReviewStatus, Role, User
from benusy_api.web import web_router

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s - %(message)s")
logger = logging.getLogger(__name__)


def _seed_default_platform_configs() -> None:
    with Session(engine) as session:
        existing_default = session.exec(
            select(PlatformMetricConfig).where(PlatformMetricConfig.platform == "default")
        ).first()
        if existing_default is None:
            session.add(PlatformMetricConfig(platform="default"))
        for platform in ["douyin", "xiaohongshu", "weibo"]:
            existing = session.exec(
                select(PlatformMetricConfig).where(PlatformMetricConfig.platform == platform)
            ).first()
            if existing is None:
                session.add(PlatformMetricConfig(platform=platform))
        session.commit()


def _seed_default_admins() -> None:
    default_admins = [
        {
            "email": "benbenbuben",
            "phone": None,
            "username": "benbenbuben",
            "display_name": "benbenbuben",
            "real_name": "benbenbuben",
        },
    ]
    with Session(engine) as session:
        existing_admin_emails = set(
            session.exec(select(User.email).where(User.role == Role.admin)).all()
        )
        for admin in default_admins:
            if admin["email"] in existing_admin_emails:
                continue
            session.add(
                User(
                    email=admin["email"],
                    phone=admin["phone"],
                    username=admin["username"],
                    display_name=admin["display_name"],
                    real_name=admin["real_name"],
                    city="N/A",
                    category="operations",
                    tags="admin",
                    follower_total=0,
                    avg_views=0,
                    hashed_password=get_password_hash("benbenbuben"),
                    role=Role.admin,
                    review_status=ReviewStatus.approved,
                )
            )
        session.commit()


@asynccontextmanager
async def lifespan(_: FastAPI):
    settings = get_settings()
    settings.ensure_data_dirs()
    if settings.DB_BOOTSTRAP_CREATE_ALL:
        create_all_tables()
    ensure_migration_state()
    _seed_default_admins()
    _seed_default_platform_configs()

    try:
        yield
    finally:
        pass
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
        "benusy_api.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.APP_ENV == "development",
    )


if __name__ == "__main__":
    run()
