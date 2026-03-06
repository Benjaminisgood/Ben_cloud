from __future__ import annotations

import logging
from pathlib import Path

from sqlalchemy import create_engine, event, inspect
from sqlalchemy.orm import sessionmaker

from ..core.config import get_settings

_logger = logging.getLogger(__name__)
_API_ROOT = Path(__file__).resolve().parents[3]


def _make_engine():
    settings = get_settings()
    db_url = settings.DATABASE_URL
    connect_args = {}
    if db_url.startswith("sqlite:///"):
        path = Path(db_url[len("sqlite:///"):])
        path.parent.mkdir(parents=True, exist_ok=True)
        connect_args = {
            "check_same_thread": False,
            "timeout": 30,
        }
    engine_obj = create_engine(db_url, connect_args=connect_args, pool_pre_ping=True)
    if "sqlite" in db_url:
        _configure_sqlite(engine_obj)
    return engine_obj


def _configure_sqlite(engine_obj) -> None:
    @event.listens_for(engine_obj, "connect")
    def _set_pragmas(dbapi_connection, connection_record):  # noqa: ANN001, ARG001
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL;")
        cursor.execute("PRAGMA synchronous=NORMAL;")
        cursor.execute("PRAGMA busy_timeout=30000;")
        cursor.close()


engine = _make_engine()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    _upgrade_schema_with_alembic()
    _seed_admin()


def _upgrade_schema_with_alembic() -> None:
    from alembic import command
    from alembic.config import Config

    alembic_ini = _API_ROOT / "alembic.ini"
    if not alembic_ini.exists():
        raise RuntimeError(f"Alembic configuration not found: {alembic_ini}")

    cfg = Config(str(alembic_ini))
    cfg.set_main_option("sqlalchemy.url", get_settings().DATABASE_URL)

    with engine.connect() as conn:
        existing_tables = set(inspect(conn).get_table_names())

    baseline_tables = {"user", "project_health", "project_click", "bug_report", "project_log"}
    if "alembic_version" not in existing_tables and baseline_tables.issubset(existing_tables):
        command.stamp(cfg, "head")
        _logger.info("检测到现有历史库，已执行 alembic stamp head 基线接管")
        return

    command.upgrade(cfg, "head")
    _logger.info("数据库迁移完成（alembic upgrade head）")


def _seed_admin() -> None:
    """启动时自动播种管理员账号。

    - 读取 .env 中的 ADMIN_USERNAME / ADMIN_PASSWORD
    - 若用户不存在则创建；若已存在但角色不是 admin 则修正
    - 若 env 未配置且数据库无任何管理员，输出 ERROR 提醒
    """
    from ..repositories import (
        create_user,
        get_user_by_username,
        has_active_admin,
        update_user_role,
    )

    settings = get_settings()
    username = (settings.ADMIN_USERNAME or "").strip()
    password = (settings.ADMIN_PASSWORD or "").strip()

    if not username or not password:
        # env 未配置凭据 —— 检查是否已有管理员，没有则报错提醒
        try:
            with SessionLocal() as db:
                has_admin = has_active_admin(db)
        except Exception as exc:
            _logger.exception("检查管理员账号时发生错误: %s", exc)
            has_admin = False

        if not has_admin:
            _logger.error(
                "⚠ .env 中未配置 ADMIN_USERNAME / ADMIN_PASSWORD，"
                "且数据库中没有任何管理员账号！"
                "请在 .env 中设置后重启服务，否则无法登录门户。"
            )
        else:
            _logger.debug("ADMIN_USERNAME 未配置，跳过播种（数据库中已有管理员账号）")
        return

    try:
        with SessionLocal() as db:
            existing = get_user_by_username(db, username)
            if existing:
                if existing.role != "admin":
                    update_user_role(db, existing, "admin")
                    _logger.info("用户 '%s' 角色已更新为 admin", username)
                else:
                    _logger.debug("管理员账号 '%s' 已存在，无需重复播种", username)
                return
            # 首次启动：创建管理员
            create_user(db, username=username, password=password, role="admin", is_active=True)
            _logger.info("✓ 首次启动：管理员账号 '%s' 已自动创建", username)
    except Exception as exc:
        _logger.exception("创建管理员账号时发生错误，请检查数据库连接: %s", exc)
