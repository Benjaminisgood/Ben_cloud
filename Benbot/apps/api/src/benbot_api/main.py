"""Benbot API application entry point."""
from __future__ import annotations

import asyncio
import contextlib
import fcntl
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Depends, FastAPI
from fastapi.responses import PlainTextResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from starlette.middleware.sessions import SessionMiddleware

from .api.router import api_router
from .core.config import get_settings
from .core.registry import validate_registry_alignment
from .db.session import SessionLocal, get_db, init_db
from .models import User
from .services.health import health_check_loop
from .services.metrics import render_prometheus_metrics
from .web.router import web_router

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s - %(message)s")
logger = logging.getLogger(__name__)


class _FileLeaderLock:
    def __init__(self, lock_file: Path) -> None:
        self._lock_file = lock_file
        self._fd = None

    def acquire(self) -> bool:
        self._lock_file.parent.mkdir(parents=True, exist_ok=True)
        self._fd = self._lock_file.open("a+")
        try:
            fcntl.flock(self._fd.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            return True
        except BlockingIOError:
            self._fd.close()
            self._fd = None
            return False

    def release(self) -> None:
        if self._fd is None:
            return
        with contextlib.suppress(Exception):
            fcntl.flock(self._fd.fileno(), fcntl.LOCK_UN)
        with contextlib.suppress(Exception):
            self._fd.close()
        self._fd = None


def _verify_admin_exists() -> None:
    """启动后校验：确保数据库中至少存在一位活跃管理员，否则输出 CRITICAL 警告。"""
    try:
        with SessionLocal() as db:
            admin_count = db.query(User).filter_by(role="admin", is_active=True).count()
        if admin_count == 0:
            logger.critical(
                "⚠⚠⚠ 数据库中没有任何管理员账号！"
                "请确认 .env 中已配置 ADMIN_USERNAME 和 ADMIN_PASSWORD，"
                "然后执行 ./benbot.sh restart 重启服务。"
            )
        else:
            logger.info("✓ 管理员账号校验通过（共 %d 位活跃管理员）", admin_count)
    except Exception as exc:
        logger.exception("管理员账号校验时发生错误: %s", exc)


@asynccontextmanager
async def lifespan(_: FastAPI):
    settings = get_settings()
    settings.ensure_data_dirs()
    settings.validate_security()
    validate_registry_alignment(settings)
    init_db()
    logger.info("数据库初始化完成")

    # 启动后二次校验：确保至少有一位可用管理员
    _verify_admin_exists()

    task: asyncio.Task | None = None
    leader_lock: _FileLeaderLock | None = None
    if settings.HEALTH_CHECK_SINGLE_LEADER:
        lock_file = settings.DATA_DIR / "health_check.lock"
        leader_lock = _FileLeaderLock(lock_file)
        if leader_lock.acquire():
            task = asyncio.create_task(health_check_loop())
            logger.info(
                "Health check loop started as leader (interval=%ss)",
                settings.HEALTH_CHECK_INTERVAL,
            )
        else:
            logger.info("Health check loop skipped in this worker (leader already active)")
    else:
        task = asyncio.create_task(health_check_loop())
        logger.info("Health check loop started (interval=%ss)", settings.HEALTH_CHECK_INTERVAL)

    try:
        yield
    finally:
        if task is not None:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
        if leader_lock is not None:
            leader_lock.release()
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

    static_dir = settings.WEB_STATIC_DIR
    if static_dir.exists():
        app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")
    else:
        logger.warning("Static dir not found: %s", static_dir)

    app.include_router(web_router)
    app.include_router(api_router)

    @app.get("/health", tags=["health"])
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/metrics", include_in_schema=False, response_class=PlainTextResponse)
    def metrics(db: Session = Depends(get_db)) -> str:
        if not settings.ENABLE_PROMETHEUS_METRICS:
            return ""
        return render_prometheus_metrics(db)

    return app


app = create_app()


def run() -> None:
    import uvicorn

    settings = get_settings()
    uvicorn.run(
        "benbot_api.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.APP_ENV == "development",
    )


if __name__ == "__main__":
    run()
