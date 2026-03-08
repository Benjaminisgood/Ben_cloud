from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from textwrap import dedent


WORKSPACE_ROOT = Path(__file__).resolve().parents[2]


@dataclass(frozen=True)
class AppSpec:
    app_dir: str
    package: str
    app_name: str
    port: int
    source_db: str
    emoji: str
    hero_title: str
    hero_subtitle: str
    focus_label: str
    focus_hint: str
    nav_label: str
    source_label: str
    primary: str
    secondary: str
    canvas: str
    ink: str
    collections_title: str
    collections_subtitle: str

    @property
    def cookie_name(self) -> str:
        return f"{self.app_dir.lower()}_session"

    @property
    def database_file(self) -> str:
        return f"{self.app_dir.lower()}.sqlite"

    @property
    def package_title(self) -> str:
        return self.package.replace("_api", "-api")


SPECS = [
    AppSpec(
        app_dir="Benprefs",
        package="benprefs_api",
        app_name="Benprefs",
        port=8800,
        source_db="preferences.db",
        emoji="💛",
        hero_title="偏好档案站",
        hero_subtitle="把你在意的事物、偏好强度和网站习惯汇总成可浏览的长期画像。",
        focus_label="偏好假说",
        focus_hint="记录值得进一步确认的偏好变化，作为 journal 提取后的人工确认层。",
        nav_label="Preferences",
        source_label="preferences.db",
        primary="#9b3d23",
        secondary="#f2a541",
        canvas="#f6eee3",
        ink="#2f2118",
        collections_title="偏好切片",
        collections_subtitle="当前偏好、网站偏好与时间线变化",
    ),
    AppSpec(
        app_dir="Benhealth",
        package="benhealth_api",
        app_name="Benhealth",
        port=8900,
        source_db="health.db",
        emoji="🫀",
        hero_title="健康仪表站",
        hero_subtitle="把运动、身体指标与营养记录整理成清晰的自我照护界面。",
        focus_label="健康检查",
        focus_hint="记录你和 agent 观察到的健康提醒、阶段目标和复盘结论。",
        nav_label="Health",
        source_label="health.db",
        primary="#0f6d62",
        secondary="#56c596",
        canvas="#e9f5ef",
        ink="#173630",
        collections_title="健康切片",
        collections_subtitle="运动、身体指标与饮食汇总",
    ),
    AppSpec(
        app_dir="Benfinance",
        package="benfinance_api",
        app_name="Benfinance",
        port=9100,
        source_db="finance.db",
        emoji="💹",
        hero_title="财务洞察站",
        hero_subtitle="把账户、交易、预算和储蓄目标收束成一套可持续追踪的资金看板。",
        focus_label="财务决策",
        focus_hint="记录重要消费、预算假设与后续动作，形成可追溯的财务思考流。",
        nav_label="Finance",
        source_label="finance.db",
        primary="#183a5a",
        secondary="#d2a44c",
        canvas="#eef3f8",
        ink="#172435",
        collections_title="财务切片",
        collections_subtitle="账户、流水、预算与储蓄目标",
    ),
]


def render(template: str, spec: AppSpec) -> str:
    mapping = {
        "APP_DIR": spec.app_dir,
        "PACKAGE": spec.package,
        "APP_NAME": spec.app_name,
        "PORT": str(spec.port),
        "SOURCE_DB": spec.source_db,
        "EMOJI": spec.emoji,
        "HERO_TITLE": spec.hero_title,
        "HERO_SUBTITLE": spec.hero_subtitle,
        "FOCUS_LABEL": spec.focus_label,
        "FOCUS_HINT": spec.focus_hint,
        "NAV_LABEL": spec.nav_label,
        "SOURCE_LABEL": spec.source_label,
        "PRIMARY": spec.primary,
        "SECONDARY": spec.secondary,
        "CANVAS": spec.canvas,
        "INK": spec.ink,
        "COOKIE_NAME": spec.cookie_name,
        "DATABASE_FILE": spec.database_file,
        "PACKAGE_TITLE": spec.package_title,
        "COLLECTIONS_TITLE": spec.collections_title,
        "COLLECTIONS_SUBTITLE": spec.collections_subtitle,
    }
    output = template
    for key, value in mapping.items():
        output = output.replace(f"@@{key}@@", value)
    if not output.endswith("\n"):
        output += "\n"
    return output


def write_file(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def shared_agents(spec: AppSpec) -> str:
    return render(
        dedent(
            """
            # AGENTS.md - @@APP_NAME@@

            ## 当前架构（唯一真实来源）

            @@APP_NAME@@ 已按 Ben_cloud FastAPI 新项目规范搭建，唯一后端代码路径：

            - `@@WORKSPACE@@/@@APP_DIR@@/apps/api/src/@@PACKAGE@@`

            ## 目录重点

            - API 入口：`apps/api/src/@@PACKAGE@@/main.py`
            - JSON/API 路由：`apps/api/src/@@PACKAGE@@/api/routes/`
            - Web 路由：`apps/api/src/@@PACKAGE@@/web/routes/`
            - 配置：`apps/api/src/@@PACKAGE@@/core/config.py`
            - 数据层：`apps/api/src/@@PACKAGE@@/db/`, `.../models/`, `.../repositories/`
            - 业务层：`apps/api/src/@@PACKAGE@@/services/`
            - 模板：`apps/web/templates/`
            - 静态资源：`apps/web/static/`
            - 数据库：`data/@@DATABASE_FILE@@`
            - 日志：`logs/`
            - 迁移：`apps/api/alembic/versions/`

            ## 启动/测试

            项目根目录：`@@WORKSPACE@@/@@APP_DIR@@`

            ```bash
            make install
            make db-upgrade
            make dev
            make test
            ```

            ## 数据库迁移规则（强制）

            1. 只允许通过 Alembic 变更 schema。
            2. 禁止在常规流程依赖 runtime `create_all`。
            3. 所有运行时数据只允许落在 `data/` 和 `logs/`。

            ## Agent 修改约束

            1. 所有后端改动落在 `@@PACKAGE@@` 包内。
            2. 新增查询放 `repositories`，业务逻辑放 `services`，路由层保持薄。
            3. 所有展示都以服务层输出的聚合视图为准，不在路由里写复杂 SQL。
            4. 先改代码再跑 `make test`；跨应用改动完成后回到工作区根执行 `make test`。
            5. 继续迭代时，遵循：
               - `@@WORKSPACE@@/PROJECT_STANDARDS/FASTAPI_ENGINEERING_STANDARD.md`
               - `@@WORKSPACE@@/PROJECT_STANDARDS/FASTAPI_UNIFICATION_PROGRESS.md`
            """
        ).replace("@@WORKSPACE@@", str(WORKSPACE_ROOT)),
        spec,
    )


def shared_makefile(spec: AppSpec) -> str:
    return render(
        dedent(
            """
            .PHONY: install dev test check migrate-smoke ci db-upgrade db-revision db-current layout-guard

            PYTEST_DISABLE_PLUGIN_AUTOLOAD ?= 1

            layout-guard:
            	test ! -d app
            	test ! -d frontend
            	test ! -d test
            	test ! -f database.db
            	test ! -f requirements.txt

            install:
            	cd apps/api && python3 -m pip install -e ".[dev]"

            dev:
            	cd apps/api && PYTHONPATH=src alembic upgrade head
            	cd apps/api && PYTHONPATH=src uvicorn @@PACKAGE@@.main:app --app-dir src --reload --host 0.0.0.0 --port @@PORT@@

            test:
            	cd apps/api && PYTEST_DISABLE_PLUGIN_AUTOLOAD=$(PYTEST_DISABLE_PLUGIN_AUTOLOAD) PYTHONPATH=src pytest -q

            check:
            	$(MAKE) layout-guard
            	cd apps/api && PYTHONPATH=src python -m compileall -q src/@@PACKAGE@@
            	cd apps/api && PYTEST_DISABLE_PLUGIN_AUTOLOAD=$(PYTEST_DISABLE_PLUGIN_AUTOLOAD) PYTHONPATH=src pytest -q
            	cd apps/api && PYTHONPATH=src alembic current

            migrate-smoke:
            	cd apps/api && DATABASE_URL=sqlite:////tmp/@@APP_DIR@@_migrate_smoke.sqlite PYTHONPATH=src alembic upgrade head
            	rm -f /tmp/@@APP_DIR@@_migrate_smoke.sqlite

            ci: check migrate-smoke

            db-upgrade:
            	cd apps/api && PYTHONPATH=src alembic upgrade head

            db-revision:
            	cd apps/api && PYTHONPATH=src alembic revision --autogenerate -m "$(m)"

            db-current:
            	cd apps/api && PYTHONPATH=src alembic current
            """
        ),
        spec,
    )


def shared_pyproject(spec: AppSpec) -> str:
    return render(
        dedent(
            """
            [build-system]
            requires = ["hatchling"]
            build-backend = "hatchling.build"

            [project]
            name = "@@PACKAGE_TITLE@@"
            version = "0.1.0"
            requires-python = ">=3.10"
            dependencies = [
                "alembic>=1.13.0",
                "fastapi>=0.115.0",
                "jinja2>=3.1.4",
                "pydantic-settings>=2.4.0",
                "python-multipart>=0.0.9",
                "sqlalchemy>=2.0.30",
                "uvicorn[standard]>=0.30.0",
            ]

            [project.optional-dependencies]
            dev = ["httpx>=0.27.0", "pytest>=8.0.0"]

            [project.scripts]
            @@PACKAGE@@ = "@@PACKAGE@@.main:run"

            [tool.hatch.build.targets.wheel]
            packages = ["src/@@PACKAGE@@"]

            [tool.hatch.build.targets.sdist]
            include = ["src/"]
            """
        ),
        spec,
    )


ALEMBIC_INI = dedent(
    """
    [alembic]
    script_location = alembic
    prepend_sys_path = src
    path_separator = os
    timezone = UTC

    [loggers]
    keys = root,sqlalchemy,alembic

    [handlers]
    keys = console

    [formatters]
    keys = generic

    [logger_root]
    level = WARN
    handlers = console

    [logger_sqlalchemy]
    level = WARN
    handlers =
    qualname = sqlalchemy.engine

    [logger_alembic]
    level = INFO
    handlers =
    qualname = alembic

    [handler_console]
    class = StreamHandler
    args = (sys.stderr,)
    level = NOTSET
    formatter = generic

    [formatter_generic]
    format = %(levelname)-5.5s [%(name)s] %(message)s
    datefmt = %H:%M:%S
    """
)


ALEMBIC_SCRIPT = dedent(
    """
    \"\"\"${message}

    Revision ID: ${up_revision}
    Revises: ${down_revision | comma,n}
    Create Date: ${create_date}
    \"\"\"
    from __future__ import annotations

    from alembic import op
    import sqlalchemy as sa
    ${imports if imports else ""}

    # revision identifiers, used by Alembic.
    revision = ${repr(up_revision)}
    down_revision = ${repr(down_revision)}
    branch_labels = ${repr(branch_labels)}
    depends_on = ${repr(depends_on)}


    def upgrade() -> None:
        ${upgrades if upgrades else "pass"}


    def downgrade() -> None:
        ${downgrades if downgrades else "pass"}
    """
)


def shared_alembic_env(spec: AppSpec) -> str:
    return render(
        dedent(
            """
            from __future__ import annotations

            from logging.config import fileConfig

            from alembic import context
            from sqlalchemy import engine_from_config, pool

            from @@PACKAGE@@.core.config import get_settings
            from @@PACKAGE@@.db.base import Base
            import @@PACKAGE@@.models  # noqa: F401

            config = context.config

            if config.config_file_name is not None:
                fileConfig(config.config_file_name)

            target_metadata = Base.metadata
            config.set_main_option("sqlalchemy.url", get_settings().DATABASE_URL)


            def run_migrations_offline() -> None:
                url = config.get_main_option("sqlalchemy.url")
                context.configure(
                    url=url,
                    target_metadata=target_metadata,
                    literal_binds=True,
                    dialect_opts={"paramstyle": "named"},
                    compare_type=True,
                )

                with context.begin_transaction():
                    context.run_migrations()


            def run_migrations_online() -> None:
                connectable = engine_from_config(
                    config.get_section(config.config_ini_section, {}),
                    prefix="sqlalchemy.",
                    poolclass=pool.NullPool,
                )

                with connectable.connect() as connection:
                    context.configure(
                        connection=connection,
                        target_metadata=target_metadata,
                        compare_type=True,
                    )

                    with context.begin_transaction():
                        context.run_migrations()


            if context.is_offline_mode():
                run_migrations_offline()
            else:
                run_migrations_online()
            """
        ),
        spec,
    )


def shared_migration(spec: AppSpec) -> str:
    return dedent(
        """
        \"\"\"initial_focus_entries

        Revision ID: 202603080001
        Revises:
        Create Date: 2026-03-08 00:00:00+00:00
        \"\"\"
        from __future__ import annotations

        from alembic import op
        import sqlalchemy as sa


        revision = "202603080001"
        down_revision = None
        branch_labels = None
        depends_on = None


        def upgrade() -> None:
            op.create_table(
                "focus_entries",
                sa.Column("id", sa.Integer(), nullable=False),
                sa.Column("title", sa.String(length=120), nullable=False),
                sa.Column("body", sa.Text(), nullable=False),
                sa.Column("priority", sa.Integer(), nullable=False, server_default="3"),
                sa.Column("status", sa.String(length=20), nullable=False, server_default="active"),
                sa.Column("created_by", sa.String(length=80), nullable=False),
                sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
                sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
                sa.PrimaryKeyConstraint("id", name=op.f("pk_focus_entries")),
            )


        def downgrade() -> None:
            op.drop_table("focus_entries")
        """
    )


def shared_package_init() -> str:
    return "__all__ = []\n"


def shared_main(spec: AppSpec) -> str:
    return render(
        dedent(
            """
            from __future__ import annotations

            from contextlib import asynccontextmanager

            from fastapi import FastAPI
            from fastapi.staticfiles import StaticFiles
            from starlette.middleware.sessions import SessionMiddleware

            from .api import api_router
            from .core.config import get_settings
            from .web import web_router


            @asynccontextmanager
            async def lifespan(_: FastAPI):
                get_settings().ensure_data_dirs()
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
                    session_cookie=settings.SESSION_COOKIE_NAME,
                    max_age=settings.REMEMBER_DAYS * 24 * 3600,
                    same_site=settings.SESSION_COOKIE_SAMESITE,
                    https_only=settings.SESSION_COOKIE_SECURE,
                )

                if settings.STATIC_DIR.exists():
                    app.mount("/static", StaticFiles(directory=str(settings.STATIC_DIR)), name="static")

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
                    "@@PACKAGE@@.main:app",
                    host=settings.HOST,
                    port=settings.PORT,
                    reload=settings.APP_ENV == "development",
                )


            if __name__ == "__main__":
                run()
            """
        ),
        spec,
    )


def shared_config(spec: AppSpec) -> str:
    return render(
        dedent(
            """
            from __future__ import annotations

            from functools import lru_cache
            from pathlib import Path

            from pydantic import Field
            from pydantic_settings import BaseSettings, SettingsConfigDict

            _REPO_ROOT = Path(__file__).resolve().parents[5]
            _WORKSPACE_ROOT = _REPO_ROOT.parent
            _DATA_DIR = _REPO_ROOT / "data"
            _LOGS_DIR = _REPO_ROOT / "logs"


            class Settings(BaseSettings):
                model_config = SettingsConfigDict(
                    env_file=str(_REPO_ROOT / ".env"),
                    env_file_encoding="utf-8",
                    extra="ignore",
                )

                APP_NAME: str = "@@APP_NAME@@"
                APP_VERSION: str = "0.1.0"
                APP_ENV: str = "development"
                API_PREFIX: str = "/api"
                HOST: str = "0.0.0.0"
                PORT: int = @@PORT@@

                SECRET_KEY: str = "dev-only-change-me"
                SSO_SECRET: str = "dev-sso-secret-change-me"
                REMEMBER_DAYS: int = 30
                SESSION_COOKIE_NAME: str = "@@COOKIE_NAME@@"
                SESSION_COOKIE_SAMESITE: str = "lax"
                SESSION_COOKIE_SECURE: bool = False

                ADMIN_USERNAME: str = "benbenbuben"
                ADMIN_PASSWORD: str = "benbenbuben"
                BENBOT_BASE_URL: str = "http://localhost:80"

                DATABASE_URL: str = f"sqlite:///{(_DATA_DIR / '@@DATABASE_FILE@@').resolve()}"
                SOURCE_DATABASE_PATH: Path = Field(default=_WORKSPACE_ROOT / "database" / "@@SOURCE_DB@@")

                STATIC_DIR: Path = _REPO_ROOT / "apps" / "web" / "static"
                TEMPLATES_DIR: Path = _REPO_ROOT / "apps" / "web" / "templates"
                LOGS_DIR: Path = _LOGS_DIR

                @property
                def REPO_ROOT(self) -> Path:
                    return _REPO_ROOT

                @property
                def DATA_DIR(self) -> Path:
                    return _DATA_DIR

                def ensure_data_dirs(self) -> None:
                    for path in (self.DATA_DIR, self.LOGS_DIR):
                        path.mkdir(parents=True, exist_ok=True)


            @lru_cache
            def get_settings() -> Settings:
                return Settings()
            """
        ),
        spec,
    )


DB_BASE = dedent(
    """
    from __future__ import annotations

    from sqlalchemy import MetaData
    from sqlalchemy.orm import DeclarativeBase

    NAMING_CONVENTION = {
        "ix": "ix_%(column_0_label)s",
        "uq": "uq_%(table_name)s_%(column_0_name)s",
        "ck": "ck_%(table_name)s_%(constraint_name)s",
        "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
        "pk": "pk_%(table_name)s",
    }


    class Base(DeclarativeBase):
        metadata = MetaData(naming_convention=NAMING_CONVENTION)
    """
)


def shared_session(spec: AppSpec) -> str:
    return render(
        dedent(
            """
            from __future__ import annotations

            from collections.abc import Generator
            from pathlib import Path

            from sqlalchemy import create_engine
            from sqlalchemy.orm import Session, sessionmaker

            from @@PACKAGE@@.core.config import get_settings


            def _make_engine():
                settings = get_settings()
                db_url = settings.DATABASE_URL
                if db_url.startswith("sqlite:///"):
                    db_path = Path(db_url[len("sqlite:///") :])
                    db_path.parent.mkdir(parents=True, exist_ok=True)
                connect_args = {"check_same_thread": False} if db_url.startswith("sqlite") else {}
                return create_engine(db_url, pool_pre_ping=True, connect_args=connect_args)


            engine = _make_engine()
            SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)


            def get_db() -> Generator[Session, None, None]:
                db = SessionLocal()
                try:
                    yield db
                finally:
                    db.close()
            """
        ),
        spec,
    )


FOCUS_MODEL = dedent(
    """
    from __future__ import annotations

    from datetime import UTC, datetime

    from sqlalchemy import DateTime, Integer, String, Text
    from sqlalchemy.orm import Mapped, mapped_column

    from ..db.base import Base


    class FocusEntry(Base):
        __tablename__ = "focus_entries"

        id: Mapped[int] = mapped_column(Integer, primary_key=True)
        title: Mapped[str] = mapped_column(String(120))
        body: Mapped[str] = mapped_column(Text)
        priority: Mapped[int] = mapped_column(Integer, default=3)
        status: Mapped[str] = mapped_column(String(20), default="active")
        created_by: Mapped[str] = mapped_column(String(80))
        created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
        updated_at: Mapped[datetime] = mapped_column(
            DateTime(timezone=True),
            default=lambda: datetime.now(UTC),
            onupdate=lambda: datetime.now(UTC),
        )
    """
)


MODELS_INIT = dedent(
    """
    from .focus_entry import FocusEntry

    __all__ = ["FocusEntry"]
    """
)


REPO_CODE = dedent(
    """
    from __future__ import annotations

    from sqlalchemy import select
    from sqlalchemy.orm import Session

    from ..models import FocusEntry
    from ..schemas.focus_entry import FocusEntryCreate


    def list_focus_entries(db: Session, *, limit: int = 20) -> list[FocusEntry]:
        stmt = select(FocusEntry).order_by(FocusEntry.created_at.desc()).limit(limit)
        return list(db.execute(stmt).scalars().all())


    def create_focus_entry(db: Session, *, payload: FocusEntryCreate, created_by: str) -> FocusEntry:
        item = FocusEntry(
            title=payload.title.strip(),
            body=payload.body.strip(),
            priority=payload.priority,
            created_by=created_by,
            status="active",
        )
        db.add(item)
        db.commit()
        db.refresh(item)
        return item
    """
)


FOCUS_SCHEMA = dedent(
    """
    from __future__ import annotations

    from datetime import datetime

    from pydantic import BaseModel, ConfigDict, Field


    class FocusEntryCreate(BaseModel):
        title: str = Field(min_length=1, max_length=120)
        body: str = Field(min_length=1, max_length=4000)
        priority: int = Field(default=3, ge=1, le=5)


    class FocusEntryRead(BaseModel):
        model_config = ConfigDict(from_attributes=True)

        id: int
        title: str
        body: str
        priority: int
        status: str
        created_by: str
        created_at: datetime
        updated_at: datetime
    """
)


DASHBOARD_SCHEMA = dedent(
    """
    from __future__ import annotations

    from pydantic import BaseModel


    class DashboardMetric(BaseModel):
        label: str
        value: str
        hint: str


    class DashboardColumn(BaseModel):
        key: str
        label: str


    class DashboardTable(BaseModel):
        title: str
        subtitle: str
        empty_message: str
        columns: list[DashboardColumn]
        rows: list[dict[str, str]]


    class DashboardSnapshot(BaseModel):
        source: str
        summary: list[DashboardMetric]
        collections: list[DashboardTable]
    """
)


SCHEMAS_INIT = dedent(
    """
    from .dashboard import DashboardSnapshot
    from .focus_entry import FocusEntryCreate, FocusEntryRead

    __all__ = ["DashboardSnapshot", "FocusEntryCreate", "FocusEntryRead"]
    """
)


def shared_sso_service(spec: AppSpec) -> str:
    return render(
        dedent(
            """
            from __future__ import annotations

            import base64
            import hashlib
            import hmac
            import json
            import time


            def verify_sso_token(sso_secret: str, token: str) -> dict | None:
                try:
                    decoded = base64.urlsafe_b64decode(token.encode()).decode()
                    dot_pos = decoded.rfind(".")
                    if dot_pos == -1:
                        return None
                    data, sig = decoded[:dot_pos], decoded[dot_pos + 1 :]
                    expected = hmac.new(sso_secret.encode(), data.encode(), hashlib.sha256).hexdigest()
                    if not hmac.compare_digest(sig, expected):
                        return None
                    payload = json.loads(data)
                    if payload.get("e", 0) < time.time():
                        return None
                    return payload
                except Exception:
                    return None
            """
        ),
        spec,
    )


def preferences_legacy_data() -> str:
    return dedent(
        """
        from __future__ import annotations

        import sqlite3
        from pathlib import Path

        from ..schemas.dashboard import DashboardSnapshot


        def _connect(source_db_path: Path) -> sqlite3.Connection:
            conn = sqlite3.connect(source_db_path)
            conn.row_factory = sqlite3.Row
            return conn


        def _scalar(conn: sqlite3.Connection, query: str) -> int | float:
            return conn.execute(query).fetchone()[0]


        def _rows(conn: sqlite3.Connection, query: str) -> list[dict[str, str]]:
            rows = []
            for row in conn.execute(query).fetchall():
                rows.append({key: "-" if row[key] in (None, "") else str(row[key]) for key in row.keys()})
            return rows


        def get_dashboard_snapshot(source_db_path: Path) -> DashboardSnapshot:
            if not source_db_path.exists():
                return DashboardSnapshot(source="preferences.db", summary=[], collections=[])

            conn = _connect(source_db_path)
            try:
                summary = [
                    {"label": "当前偏好", "value": str(_scalar(conn, "SELECT COUNT(*) FROM preference_items WHERE is_current = 1")), "hint": "仍在持续成立的偏好条目"},
                    {"label": "正向偏好", "value": str(_scalar(conn, "SELECT COUNT(*) FROM preference_items WHERE is_current = 1 AND is_positive = 1")), "hint": "明确喜欢并持续保持的偏好"},
                    {"label": "网站偏好", "value": str(_scalar(conn, "SELECT COUNT(*) FROM website_preferences WHERE is_current = 1")), "hint": "正在使用或仍有态度的网站/平台"},
                    {"label": "偏好时间线", "value": str(_scalar(conn, "SELECT COUNT(*) FROM preference_timeline")), "hint": "已记录的偏好变化节点"},
                ]
                collections = [
                    {
                        "title": "当前偏好条目",
                        "subtitle": "偏好强度和标签，适合做 agent 用户画像的稳定层",
                        "empty_message": "preferences.db 里还没有当前偏好条目",
                        "columns": [
                            {"key": "name", "label": "偏好"},
                            {"key": "direction", "label": "方向"},
                            {"key": "intensity", "label": "强度"},
                            {"key": "tags", "label": "标签"},
                        ],
                        "rows": _rows(
                            conn,
                            '''
                            SELECT
                                name,
                                CASE WHEN is_positive = 1 THEN '喜欢' ELSE '规避' END AS direction,
                                intensity || '/10' AS intensity,
                                COALESCE(tags, '-') AS tags
                            FROM preference_items
                            WHERE is_current = 1
                            ORDER BY COALESCE(last_updated, updated_at) DESC, id DESC
                            LIMIT 8
                            ''',
                        ),
                    },
                    {
                        "title": "网站偏好",
                        "subtitle": "把常用网站和平台偏好独立出来，方便做上下文路由",
                        "empty_message": "preferences.db 里还没有网站偏好",
                        "columns": [
                            {"key": "name", "label": "网站"},
                            {"key": "category", "label": "类别"},
                            {"key": "usage_frequency", "label": "频率"},
                            {"key": "intensity", "label": "偏好强度"},
                        ],
                        "rows": _rows(
                            conn,
                            '''
                            SELECT
                                name,
                                COALESCE(category, '-') AS category,
                                COALESCE(usage_frequency, '-') AS usage_frequency,
                                intensity || '/10' AS intensity
                            FROM website_preferences
                            WHERE is_current = 1
                            ORDER BY updated_at DESC, id DESC
                            LIMIT 8
                            ''',
                        ),
                    },
                ]
                return DashboardSnapshot(source="preferences.db", summary=summary, collections=collections)
            finally:
                conn.close()
        """
    )


def health_legacy_data() -> str:
    return dedent(
        """
        from __future__ import annotations

        import sqlite3
        from pathlib import Path

        from ..schemas.dashboard import DashboardSnapshot


        def _connect(source_db_path: Path) -> sqlite3.Connection:
            conn = sqlite3.connect(source_db_path)
            conn.row_factory = sqlite3.Row
            return conn


        def _scalar(conn: sqlite3.Connection, query: str) -> int | float:
            value = conn.execute(query).fetchone()[0]
            return value or 0


        def _rows(conn: sqlite3.Connection, query: str) -> list[dict[str, str]]:
            rows = []
            for row in conn.execute(query).fetchall():
                rows.append({key: "-" if row[key] in (None, "") else str(row[key]) for key in row.keys()})
            return rows


        def get_dashboard_snapshot(source_db_path: Path) -> DashboardSnapshot:
            if not source_db_path.exists():
                return DashboardSnapshot(source="health.db", summary=[], collections=[])

            conn = _connect(source_db_path)
            try:
                total_minutes = _scalar(conn, "SELECT COALESCE(SUM(duration_minutes), 0) FROM workouts")
                summary = [
                    {"label": "运动记录", "value": str(_scalar(conn, "SELECT COUNT(*) FROM workouts")), "hint": "累计运动次数"},
                    {"label": "总时长", "value": f"{int(total_minutes)} 分钟", "hint": "已记录的运动总时长"},
                    {"label": "营养日", "value": str(_scalar(conn, "SELECT COUNT(*) FROM daily_nutrition_summary")), "hint": "有营养汇总的日期数"},
                    {"label": "健康目标", "value": str(_scalar(conn, "SELECT COUNT(*) FROM health_goals WHERE status = 'active'")), "hint": "仍在推进的健康目标"},
                ]
                collections = [
                    {
                        "title": "最近运动",
                        "subtitle": "把强度、时长和状态变化放在同一张表里",
                        "empty_message": "health.db 里还没有运动记录",
                        "columns": [
                            {"key": "start_time", "label": "开始时间"},
                            {"key": "duration_minutes", "label": "时长"},
                            {"key": "intensity", "label": "强度"},
                            {"key": "post_workout_mood", "label": "结束状态"},
                        ],
                        "rows": _rows(
                            conn,
                            '''
                            SELECT
                                start_time,
                                duration_minutes || ' 分钟' AS duration_minutes,
                                COALESCE(intensity, '-') AS intensity,
                                COALESCE(post_workout_mood, '-') AS post_workout_mood
                            FROM workouts
                            ORDER BY start_time DESC, id DESC
                            LIMIT 8
                            ''',
                        ),
                    },
                    {
                        "title": "身体指标与营养",
                        "subtitle": "最近一次身体指标，加上最近营养汇总",
                        "empty_message": "health.db 里还没有身体指标或营养汇总",
                        "columns": [
                            {"key": "date", "label": "日期"},
                            {"key": "weight", "label": "体重/BMI"},
                            {"key": "cardio", "label": "静息心率/饮水"},
                            {"key": "energy", "label": "热量/蛋白质"},
                        ],
                        "rows": _rows(
                            conn,
                            '''
                            SELECT
                                COALESCE(strftime('%Y-%m-%d', recorded_at), date) AS date,
                                CASE
                                    WHEN weight IS NOT NULL THEN printf('%.1fkg / BMI %.1f', weight, bmi)
                                    ELSE '-'
                                END AS weight,
                                CASE
                                    WHEN resting_heart_rate IS NOT NULL THEN resting_heart_rate || ' bpm'
                                    ELSE water_ml || ' ml'
                                END AS cardio,
                                CASE
                                    WHEN total_calories IS NOT NULL THEN printf('%.0fkcal / %.1fg', total_calories, total_protein)
                                    ELSE '-'
                                END AS energy
                            FROM (
                                SELECT recorded_at, weight, bmi, resting_heart_rate, NULL AS date, NULL AS total_calories, NULL AS total_protein, NULL AS water_ml
                                FROM body_metrics
                                UNION ALL
                                SELECT NULL AS recorded_at, NULL AS weight, NULL AS bmi, NULL AS resting_heart_rate, date, total_calories, total_protein, water_ml
                                FROM daily_nutrition_summary
                            )
                            ORDER BY date DESC, recorded_at DESC
                            LIMIT 8
                            ''',
                        ),
                    },
                ]
                return DashboardSnapshot(source="health.db", summary=summary, collections=collections)
            finally:
                conn.close()
        """
    )


def finance_legacy_data() -> str:
    return dedent(
        """
        from __future__ import annotations

        import sqlite3
        from pathlib import Path

        from ..schemas.dashboard import DashboardSnapshot


        def _connect(source_db_path: Path) -> sqlite3.Connection:
            conn = sqlite3.connect(source_db_path)
            conn.row_factory = sqlite3.Row
            return conn


        def _scalar(conn: sqlite3.Connection, query: str) -> int | float:
            value = conn.execute(query).fetchone()[0]
            return value or 0


        def _rows(conn: sqlite3.Connection, query: str) -> list[dict[str, str]]:
            rows = []
            for row in conn.execute(query).fetchall():
                rows.append({key: "-" if row[key] in (None, "") else str(row[key]) for key in row.keys()})
            return rows


        def get_dashboard_snapshot(source_db_path: Path) -> DashboardSnapshot:
            if not source_db_path.exists():
                return DashboardSnapshot(source="finance.db", summary=[], collections=[])

            conn = _connect(source_db_path)
            try:
                total_balance = _scalar(conn, "SELECT COALESCE(SUM(current_balance), 0) FROM accounts WHERE is_active = 1")
                summary = [
                    {"label": "活跃账户", "value": str(_scalar(conn, "SELECT COUNT(*) FROM accounts WHERE is_active = 1")), "hint": "当前仍在使用的账户数"},
                    {"label": "总余额", "value": f"¥{total_balance:,.2f}", "hint": "账户 current_balance 汇总"},
                    {"label": "交易流水", "value": str(_scalar(conn, "SELECT COUNT(*) FROM transactions")), "hint": "已记录的交易总数"},
                    {"label": "储蓄目标", "value": str(_scalar(conn, "SELECT COUNT(*) FROM savings_goals WHERE is_completed = 0")), "hint": "仍在进行中的储蓄目标"},
                ]
                collections = [
                    {
                        "title": "账户概览",
                        "subtitle": "先看资金分布，再看流水和预算",
                        "empty_message": "finance.db 里还没有账户",
                        "columns": [
                            {"key": "name", "label": "账户"},
                            {"key": "institution", "label": "机构"},
                            {"key": "currency", "label": "币种"},
                            {"key": "current_balance", "label": "余额"},
                        ],
                        "rows": _rows(
                            conn,
                            '''
                            SELECT
                                name,
                                COALESCE(institution, '-') AS institution,
                                currency,
                                printf('¥%.2f', current_balance) AS current_balance
                            FROM accounts
                            WHERE is_active = 1
                            ORDER BY current_balance DESC, id DESC
                            LIMIT 8
                            ''',
                        ),
                    },
                    {
                        "title": "最近交易与预算",
                        "subtitle": "让近期支出、预算和目标在一个视图里对齐",
                        "empty_message": "finance.db 里还没有交易、预算或储蓄目标",
                        "columns": [
                            {"key": "date", "label": "日期"},
                            {"key": "name", "label": "条目"},
                            {"key": "type", "label": "类型"},
                            {"key": "amount", "label": "金额"},
                        ],
                        "rows": _rows(
                            conn,
                            '''
                            SELECT
                                transaction_date AS date,
                                COALESCE(description, merchant, payee, '交易记录') AS name,
                                type,
                                printf('¥%.2f', amount) AS amount
                            FROM transactions
                            UNION ALL
                            SELECT
                                start_date AS date,
                                name,
                                'budget' AS type,
                                printf('¥%.2f', amount) AS amount
                            FROM budgets
                            UNION ALL
                            SELECT
                                deadline AS date,
                                name,
                                'goal' AS type,
                                printf('¥%.2f / 已有 %.2f', target_amount, current_amount) AS amount
                            FROM savings_goals
                            ORDER BY date DESC
                            LIMIT 8
                            ''',
                        ),
                    },
                ]
                return DashboardSnapshot(source="finance.db", summary=summary, collections=collections)
            finally:
                conn.close()
        """
    )


def shared_api_init() -> str:
    return "from .router import router as api_router\n\n__all__ = [\"api_router\"]\n"


def shared_api_router(spec: AppSpec) -> str:
    return render(
        dedent(
            """
            from __future__ import annotations

            from fastapi import APIRouter

            from @@PACKAGE@@.core.config import get_settings

            from .routes import dashboard, focus_entries, system

            router = APIRouter(prefix=get_settings().API_PREFIX)
            router.include_router(system.router)
            router.include_router(dashboard.router)
            router.include_router(focus_entries.router)
            """
        ),
        spec,
    )


def shared_api_deps(spec: AppSpec) -> str:
    return render(
        dedent(
            """
            from __future__ import annotations

            from fastapi import Depends, HTTPException, Request
            from sqlalchemy.orm import Session

            from @@PACKAGE@@.db.session import get_db as get_db_session


            def get_db() -> Session:
                return next(get_db_session())


            def require_user(request: Request) -> dict[str, str]:
                user = request.session.get("user")
                if not user:
                    raise HTTPException(status_code=401, detail="auth_required")
                return user
            """
        ),
        spec,
    )


SYSTEM_ROUTE = dedent(
    """
    from __future__ import annotations

    from fastapi import APIRouter

    router = APIRouter(tags=["system"])


    @router.get("/health")
    def api_health() -> dict[str, str]:
        return {"status": "ok"}
    """
)


def shared_dashboard_route(spec: AppSpec) -> str:
    return render(
        dedent(
            """
            from __future__ import annotations

            from fastapi import APIRouter, Depends

            from @@PACKAGE@@.api.deps import require_user
            from @@PACKAGE@@.core.config import get_settings
            from @@PACKAGE@@.schemas.dashboard import DashboardSnapshot
            from @@PACKAGE@@.services.legacy_data import get_dashboard_snapshot

            router = APIRouter(tags=["dashboard"])


            @router.get("/dashboard", response_model=DashboardSnapshot)
            def dashboard(_: dict[str, str] = Depends(require_user)) -> DashboardSnapshot:
                settings = get_settings()
                return get_dashboard_snapshot(settings.SOURCE_DATABASE_PATH)
            """
        ),
        spec,
    )


def shared_focus_entries_route(spec: AppSpec) -> str:
    return render(
        dedent(
            """
            from __future__ import annotations

            from fastapi import APIRouter, Depends, status
            from sqlalchemy.orm import Session

            from @@PACKAGE@@.api.deps import require_user
            from @@PACKAGE@@.db.session import get_db
            from @@PACKAGE@@.repositories.focus_entries_repo import create_focus_entry, list_focus_entries
            from @@PACKAGE@@.schemas.focus_entry import FocusEntryCreate, FocusEntryRead

            router = APIRouter(tags=["focus_entries"])


            @router.get("/focus-entries", response_model=list[FocusEntryRead])
            def get_focus_entries(
                _: dict[str, str] = Depends(require_user),
                db: Session = Depends(get_db),
            ) -> list[FocusEntryRead]:
                return list_focus_entries(db)


            @router.post("/focus-entries", response_model=FocusEntryRead, status_code=status.HTTP_201_CREATED)
            def post_focus_entry(
                payload: FocusEntryCreate,
                user: dict[str, str] = Depends(require_user),
                db: Session = Depends(get_db),
            ) -> FocusEntryRead:
                return create_focus_entry(db, payload=payload, created_by=user["username"])
            """
        ),
        spec,
    )


ROUTES_INIT = dedent(
    """
    __all__ = []
    """
)


def shared_web_init() -> str:
    return "from .router import router as web_router\n\n__all__ = [\"web_router\"]\n"


def shared_web_router(spec: AppSpec) -> str:
    return render(
        dedent(
            """
            from __future__ import annotations

            from fastapi import APIRouter

            from .routes import auth, pages

            router = APIRouter()
            router.include_router(auth.router)
            router.include_router(pages.router)
            """
        ),
        spec,
    )


def shared_templating(spec: AppSpec) -> str:
    return render(
        dedent(
            """
            from __future__ import annotations

            from fastapi import Request
            from fastapi.responses import HTMLResponse
            from fastapi.templating import Jinja2Templates

            from @@PACKAGE@@.core.config import get_settings

            templates = Jinja2Templates(directory=str(get_settings().TEMPLATES_DIR))


            def render_template(
                request: Request,
                template_name: str,
                context: dict | None = None,
                *,
                status_code: int = 200,
            ) -> HTMLResponse:
                payload = {"request": request}
                if context:
                    payload.update(context)
                return templates.TemplateResponse(template_name, payload, status_code=status_code)
            """
        ),
        spec,
    )


WEB_DEPS = dedent(
    """
    from __future__ import annotations

    from fastapi import Request


    def get_session_user(request: Request) -> dict[str, str] | None:
        user = request.session.get("user")
        if not isinstance(user, dict):
            return None
        return {"username": str(user.get("username", "")), "role": str(user.get("role", "user"))}


    def login_session(request: Request, *, username: str, role: str) -> None:
        request.session["user"] = {"username": username, "role": role}


    def logout_session(request: Request) -> None:
        request.session.clear()
    """
)


def shared_auth_routes(spec: AppSpec) -> str:
    return render(
        dedent(
            """
            from __future__ import annotations

            from fastapi import APIRouter, Query, Request
            from fastapi.responses import HTMLResponse, RedirectResponse

            from @@PACKAGE@@.core.config import get_settings
            from @@PACKAGE@@.services.sso import verify_sso_token

            from ..deps import get_session_user, login_session, logout_session
            from ..templating import render_template

            router = APIRouter(tags=["auth"])


            @router.get("/login", response_class=HTMLResponse)
            def login_page(request: Request, error: str | None = None, sso: str | None = None):
                current_user = get_session_user(request)
                if current_user:
                    return RedirectResponse("/", status_code=303)
                message = None
                if error:
                    message = "账号或密码错误，请重试。"
                if sso:
                    message = "Benbot SSO 凭证无效或已过期，请重新登录。"
                return render_template(
                    request,
                    "login.html",
                    {
                        "title": "@@APP_NAME@@ 登录",
                        "error_message": message,
                    },
                )


            @router.post("/login")
            async def login(request: Request):
                form = await request.form()
                username = str(form.get("username", "")).strip()
                password = str(form.get("password", ""))
                next_url = str(form.get("next", "/")).strip() or "/"
                settings = get_settings()
                if username != settings.ADMIN_USERNAME or password != settings.ADMIN_PASSWORD:
                    return RedirectResponse("/login?error=invalid", status_code=303)
                login_session(request, username=username, role="admin")
                return RedirectResponse(next_url, status_code=303)


            @router.get("/logout")
            def logout(request: Request):
                logout_session(request)
                return RedirectResponse("/login", status_code=303)


            @router.get("/auth/sso")
            def sso_callback(token: str = Query(...), request: Request = None):
                settings = get_settings()
                payload = verify_sso_token(settings.SSO_SECRET, token)
                if not payload:
                    return RedirectResponse("/login?sso=invalid", status_code=303)

                username = str(payload.get("u", "")).strip()
                if not username:
                    return RedirectResponse("/login?sso=invalid", status_code=303)

                role = "admin" if str(payload.get("r", "user")) == "admin" else "user"
                login_session(request, username=username, role=role)
                return RedirectResponse("/", status_code=303)
            """
        ),
        spec,
    )


def shared_pages_routes(spec: AppSpec) -> str:
    return render(
        dedent(
            """
            from __future__ import annotations

            from fastapi import APIRouter, Depends, Request
            from fastapi.responses import HTMLResponse, RedirectResponse
            from sqlalchemy.orm import Session

            from @@PACKAGE@@.core.config import get_settings
            from @@PACKAGE@@.db.session import get_db
            from @@PACKAGE@@.repositories.focus_entries_repo import create_focus_entry, list_focus_entries
            from @@PACKAGE@@.schemas.focus_entry import FocusEntryCreate
            from @@PACKAGE@@.services.legacy_data import get_dashboard_snapshot

            from ..deps import get_session_user
            from ..templating import render_template

            router = APIRouter(tags=["pages"])


            @router.get("/", response_class=HTMLResponse)
            def dashboard(request: Request, db: Session = Depends(get_db)):
                user = get_session_user(request)
                if not user:
                    return RedirectResponse("/login", status_code=303)
                settings = get_settings()
                dashboard = get_dashboard_snapshot(settings.SOURCE_DATABASE_PATH).model_dump()
                focus_entries = [item for item in list_focus_entries(db)]
                return render_template(
                    request,
                    "dashboard.html",
                    {
                        "title": "@@APP_NAME@@",
                        "nav_label": "@@NAV_LABEL@@",
                        "hero_title": "@@EMOJI@@ @@HERO_TITLE@@",
                        "hero_subtitle": "@@HERO_SUBTITLE@@",
                        "collections_title": "@@COLLECTIONS_TITLE@@",
                        "collections_subtitle": "@@COLLECTIONS_SUBTITLE@@",
                        "focus_label": "@@FOCUS_LABEL@@",
                        "focus_hint": "@@FOCUS_HINT@@",
                        "dashboard": dashboard,
                        "focus_entries": focus_entries,
                        "current_user": user,
                        "theme": {
                            "primary": "@@PRIMARY@@",
                            "secondary": "@@SECONDARY@@",
                            "canvas": "@@CANVAS@@",
                            "ink": "@@INK@@",
                        },
                    },
                )


            @router.get("/portal")
            def portal() -> RedirectResponse:
                return RedirectResponse("/", status_code=303)


            @router.post("/focus-entries")
            async def submit_focus_entry(request: Request, db: Session = Depends(get_db)):
                user = get_session_user(request)
                if not user:
                    return RedirectResponse("/login", status_code=303)
                form = await request.form()
                title = str(form.get("title", "")).strip()
                body = str(form.get("body", "")).strip()
                try:
                    priority = int(form.get("priority", "3"))
                except ValueError:
                    priority = 3
                if not title or not body:
                    return RedirectResponse("/", status_code=303)
                payload = FocusEntryCreate(title=title, body=body, priority=priority)
                create_focus_entry(db, payload=payload, created_by=user["username"])
                return RedirectResponse("/", status_code=303)
            """
        ),
        spec,
    )


BASE_HTML = dedent(
    """
    <!doctype html>
    <html lang="zh-CN">
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <title>{{ title }}</title>
        <style>
            :root {
                --primary: {{ theme.primary if theme else '@@PRIMARY@@' }};
                --secondary: {{ theme.secondary if theme else '@@SECONDARY@@' }};
                --canvas: {{ theme.canvas if theme else '@@CANVAS@@' }};
                --ink: {{ theme.ink if theme else '@@INK@@' }};
            }
        </style>
        <link rel="stylesheet" href="/static/styles.css">
    </head>
    <body>
        {% block body %}{% endblock %}
    </body>
    </html>
    """
)


DASHBOARD_HTML = dedent(
    """
    {% extends "base.html" %}
    {% block body %}
    <div class="page-shell">
        <header class="topbar">
            <div>
                <p class="eyebrow">{{ nav_label }}</p>
                <h1>{{ hero_title }}</h1>
                <p class="subtitle">{{ hero_subtitle }}</p>
            </div>
            <div class="session-card">
                <p class="session-role">{{ current_user.role }}</p>
                <p class="session-user">{{ current_user.username }}</p>
                <a class="ghost-link" href="/logout">退出</a>
            </div>
        </header>

        <section class="summary-grid">
            {% for card in dashboard.summary %}
            <article class="metric-card">
                <p class="metric-label">{{ card.label }}</p>
                <p class="metric-value">{{ card.value }}</p>
                <p class="metric-hint">{{ card.hint }}</p>
            </article>
            {% endfor %}
        </section>

        <section class="content-grid">
            <div class="collections-panel">
                <div class="section-heading">
                    <p class="eyebrow">{{ collections_title }}</p>
                    <h2>{{ collections_subtitle }}</h2>
                </div>
                {% for table in dashboard.collections %}
                <article class="data-card">
                    <div class="card-header">
                        <h3>{{ table.title }}</h3>
                        <p>{{ table.subtitle }}</p>
                    </div>
                    {% if table.rows %}
                    <div class="table-wrap">
                        <table>
                            <thead>
                                <tr>
                                    {% for column in table.columns %}
                                    <th>{{ column.label }}</th>
                                    {% endfor %}
                                </tr>
                            </thead>
                            <tbody>
                                {% for row in table.rows %}
                                <tr>
                                    {% for column in table.columns %}
                                    <td>{{ row[column.key] }}</td>
                                    {% endfor %}
                                </tr>
                                {% endfor %}
                            </tbody>
                        </table>
                    </div>
                    {% else %}
                    <p class="empty-state">{{ table.empty_message }}</p>
                    {% endif %}
                </article>
                {% endfor %}
            </div>

            <aside class="focus-panel">
                <div class="section-heading">
                    <p class="eyebrow">{{ focus_label }}</p>
                    <h2>人工确认层</h2>
                    <p>{{ focus_hint }}</p>
                </div>
                <form class="focus-form" method="post" action="/focus-entries">
                    <label>
                        标题
                        <input type="text" name="title" required maxlength="120" placeholder="例如：偏好开始往深度工作倾斜">
                    </label>
                    <label>
                        说明
                        <textarea name="body" rows="5" required placeholder="写下你为什么要记录这条结论，以及后续怎么验证。"></textarea>
                    </label>
                    <label>
                        优先级
                        <select name="priority">
                            <option value="5">5 - 最高</option>
                            <option value="4">4 - 较高</option>
                            <option value="3" selected>3 - 常规</option>
                            <option value="2">2 - 低</option>
                            <option value="1">1 - 最低</option>
                        </select>
                    </label>
                    <button type="submit">写入 {{ focus_label }}</button>
                </form>

                <div class="focus-list">
                    {% if focus_entries %}
                    {% for item in focus_entries %}
                    <article class="focus-entry">
                        <div class="focus-meta">
                            <span>P{{ item.priority }}</span>
                            <span>{{ item.created_by }}</span>
                        </div>
                        <h3>{{ item.title }}</h3>
                        <p>{{ item.body }}</p>
                    </article>
                    {% endfor %}
                    {% else %}
                    <p class="empty-state">还没有人工确认条目。先从一条最重要的判断开始。</p>
                    {% endif %}
                </div>
            </aside>
        </section>
    </div>
    {% endblock %}
    """
)


LOGIN_HTML = dedent(
    """
    {% extends "base.html" %}
    {% block body %}
    <div class="login-shell">
        <section class="login-card">
            <p class="eyebrow">Private Access</p>
            <h1>进入 @@APP_NAME@@</h1>
            <p class="subtitle">本网站优先承载你的个人数据视图，也可通过 Benbot SSO 进入。</p>
            {% if error_message %}
            <div class="flash flash-error">{{ error_message }}</div>
            {% endif %}
            <form method="post" action="/login" class="login-form">
                <label>
                    用户名
                    <input type="text" name="username" autocomplete="username" required>
                </label>
                <label>
                    密码
                    <input type="password" name="password" autocomplete="current-password" required>
                </label>
                <input type="hidden" name="next" value="/">
                <button type="submit">本地登录</button>
            </form>
        </section>
    </div>
    {% endblock %}
    """
)


STYLES_CSS = dedent(
    """
    * {
        box-sizing: border-box;
    }

    body {
        margin: 0;
        min-height: 100vh;
        font-family: "Avenir Next", "PingFang SC", "Noto Sans SC", sans-serif;
        background:
            radial-gradient(circle at top left, color-mix(in srgb, var(--secondary) 28%, transparent), transparent 34%),
            linear-gradient(180deg, #ffffff 0%, var(--canvas) 100%);
        color: var(--ink);
    }

    a {
        color: inherit;
    }

    .page-shell,
    .login-shell {
        width: min(1180px, calc(100vw - 32px));
        margin: 0 auto;
        padding: 32px 0 56px;
    }

    .topbar,
    .content-grid {
        display: grid;
        gap: 24px;
    }

    .topbar {
        grid-template-columns: minmax(0, 1.4fr) minmax(260px, 0.6fr);
        align-items: start;
        margin-bottom: 28px;
    }

    .eyebrow {
        margin: 0 0 8px;
        font-size: 0.78rem;
        letter-spacing: 0.18em;
        text-transform: uppercase;
        color: color-mix(in srgb, var(--primary) 78%, black 12%);
    }

    h1,
    h2,
    h3,
    p {
        margin: 0;
    }

    h1 {
        font-size: clamp(2.2rem, 5vw, 4rem);
        line-height: 0.95;
        letter-spacing: -0.04em;
    }

    .subtitle {
        max-width: 54rem;
        margin-top: 12px;
        color: color-mix(in srgb, var(--ink) 74%, white 26%);
        line-height: 1.6;
    }

    .session-card,
    .metric-card,
    .data-card,
    .focus-panel,
    .login-card {
        border: 1px solid color-mix(in srgb, var(--primary) 14%, transparent);
        border-radius: 24px;
        background: rgba(255, 255, 255, 0.86);
        backdrop-filter: blur(16px);
        box-shadow: 0 18px 42px rgba(14, 30, 56, 0.08);
    }

    .session-card {
        padding: 18px 20px;
        text-align: right;
    }

    .session-role {
        font-size: 0.8rem;
        text-transform: uppercase;
        letter-spacing: 0.18em;
        color: var(--primary);
    }

    .session-user {
        margin-top: 8px;
        font-size: 1.15rem;
        font-weight: 700;
    }

    .ghost-link {
        display: inline-flex;
        margin-top: 14px;
        text-decoration: none;
        color: color-mix(in srgb, var(--primary) 92%, black 8%);
    }

    .summary-grid {
        display: grid;
        grid-template-columns: repeat(4, minmax(0, 1fr));
        gap: 16px;
        margin-bottom: 24px;
    }

    .metric-card {
        padding: 18px;
    }

    .metric-label {
        font-size: 0.9rem;
        color: color-mix(in srgb, var(--ink) 64%, white 36%);
    }

    .metric-value {
        margin-top: 14px;
        font-size: clamp(1.55rem, 2vw, 2.2rem);
        font-weight: 700;
        letter-spacing: -0.04em;
    }

    .metric-hint {
        margin-top: 10px;
        line-height: 1.5;
        color: color-mix(in srgb, var(--ink) 68%, white 32%);
    }

    .content-grid {
        grid-template-columns: minmax(0, 1.35fr) minmax(320px, 0.65fr);
    }

    .collections-panel,
    .focus-panel {
        display: grid;
        gap: 16px;
    }

    .section-heading {
        padding: 4px 2px;
    }

    .section-heading h2 {
        font-size: 1.45rem;
        letter-spacing: -0.04em;
    }

    .section-heading p:last-child {
        margin-top: 8px;
        color: color-mix(in srgb, var(--ink) 68%, white 32%);
        line-height: 1.5;
    }

    .data-card,
    .focus-panel {
        padding: 18px;
    }

    .card-header p {
        margin-top: 8px;
        line-height: 1.5;
        color: color-mix(in srgb, var(--ink) 68%, white 32%);
    }

    .table-wrap {
        margin-top: 16px;
        overflow-x: auto;
    }

    table {
        width: 100%;
        border-collapse: collapse;
        font-size: 0.95rem;
    }

    th,
    td {
        padding: 12px 10px;
        border-bottom: 1px solid color-mix(in srgb, var(--primary) 12%, transparent);
        text-align: left;
        vertical-align: top;
    }

    th {
        font-size: 0.82rem;
        text-transform: uppercase;
        letter-spacing: 0.14em;
        color: color-mix(in srgb, var(--ink) 62%, white 38%);
    }

    .focus-form,
    .login-form {
        display: grid;
        gap: 14px;
    }

    .focus-form label,
    .login-form label {
        display: grid;
        gap: 8px;
        font-size: 0.92rem;
        font-weight: 600;
    }

    input,
    textarea,
    select,
    button {
        font: inherit;
    }

    input,
    textarea,
    select {
        width: 100%;
        border: 1px solid color-mix(in srgb, var(--primary) 18%, transparent);
        border-radius: 16px;
        padding: 12px 14px;
        background: rgba(255, 255, 255, 0.92);
    }

    textarea {
        resize: vertical;
        min-height: 132px;
    }

    button {
        border: 0;
        border-radius: 999px;
        padding: 12px 18px;
        cursor: pointer;
        color: white;
        background: linear-gradient(135deg, var(--primary), var(--secondary));
        box-shadow: 0 14px 30px color-mix(in srgb, var(--primary) 32%, transparent);
    }

    .focus-list {
        display: grid;
        gap: 12px;
        margin-top: 10px;
    }

    .focus-entry {
        padding: 14px 16px;
        border-radius: 18px;
        background: color-mix(in srgb, var(--canvas) 54%, white 46%);
        border: 1px solid color-mix(in srgb, var(--primary) 10%, transparent);
    }

    .focus-meta {
        display: flex;
        gap: 10px;
        font-size: 0.78rem;
        letter-spacing: 0.08em;
        text-transform: uppercase;
        color: color-mix(in srgb, var(--ink) 62%, white 38%);
        margin-bottom: 8px;
    }

    .focus-entry p,
    .empty-state,
    .flash {
        margin-top: 8px;
        line-height: 1.55;
        color: color-mix(in srgb, var(--ink) 72%, white 28%);
    }

    .login-shell {
        display: grid;
        place-items: center;
        min-height: 100vh;
    }

    .login-card {
        width: min(520px, 100%);
        padding: 32px;
    }

    .flash-error {
        padding: 12px 14px;
        border-radius: 16px;
        background: #fff1ee;
        color: #8f2d1f;
    }

    @media (max-width: 960px) {
        .topbar,
        .content-grid,
        .summary-grid {
            grid-template-columns: 1fr;
        }

        .session-card {
            text-align: left;
        }
    }
    """
)


TESTS_CONFTEST = dedent(
    """
    from __future__ import annotations

    import importlib
    import os
    import sys
    from pathlib import Path

    import pytest
    from alembic import command
    from alembic.config import Config
    from fastapi.testclient import TestClient

    API_SRC_DIR = Path(__file__).resolve().parents[1] / "src"
    if str(API_SRC_DIR) not in sys.path:
        sys.path.insert(0, str(API_SRC_DIR))


    def _run_migrations(database_url: str) -> None:
        config = Config(str(Path(__file__).resolve().parents[1] / "alembic.ini"))
        config.set_main_option("sqlalchemy.url", database_url)
        command.upgrade(config, "head")


    @pytest.fixture()
    def client(tmp_path: Path):
        db_path = tmp_path / "@@APP_DIR@@-test.sqlite"
        source_db = Path(__file__).resolve().parents[4] / "database" / "@@SOURCE_DB@@"
        os.environ["DATABASE_URL"] = f"sqlite:///{db_path}"
        os.environ["SOURCE_DATABASE_PATH"] = str(source_db)
        os.environ["APP_ENV"] = "test"
        os.environ["SECRET_KEY"] = "test-secret-key"
        os.environ["SSO_SECRET"] = "test-sso-secret"

        import @@PACKAGE@@.core.config as config_module

        config_module.get_settings.cache_clear()
        _run_migrations(os.environ["DATABASE_URL"])

        import @@PACKAGE@@.db.session as session_module

        session_module = importlib.reload(session_module)

        import @@PACKAGE@@.main as main_module

        main_module = importlib.reload(main_module)

        with TestClient(main_module.create_app()) as test_client:
            yield test_client

        config_module.get_settings.cache_clear()
    """
)


TEST_HEALTH = dedent(
    """
    from __future__ import annotations


    def test_health(client):
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}


    def test_api_health(client):
        response = client.get("/api/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}
    """
)


def shared_test_auth(spec: AppSpec) -> str:
    return render(
        dedent(
            """
            from __future__ import annotations

            import base64
            import hashlib
            import hmac
            import json
            import time


            def _make_token(username: str, role: str) -> str:
                payload = {"u": username, "r": role, "e": int(time.time()) + 30, "n": "abcdef12"}
                data = json.dumps(payload, separators=(",", ":"))
                sig = hmac.new(b"test-sso-secret", data.encode(), hashlib.sha256).hexdigest()
                return base64.urlsafe_b64encode(f"{data}.{sig}".encode()).decode()


            def test_dashboard_requires_login(client):
                response = client.get("/", follow_redirects=False)
                assert response.status_code == 303
                assert response.headers["location"] == "/login"


            def test_sso_login_allows_dashboard_access(client):
                token = _make_token("agent-user", "admin")
                response = client.get(f"/auth/sso?token={token}", follow_redirects=False)
                assert response.status_code == 303
                assert response.headers["location"] == "/"

                dashboard = client.get("/api/dashboard")
                assert dashboard.status_code == 200
                assert dashboard.json()["source"] == "@@SOURCE_DB@@"
            """
        ),
        spec,
    )


TEST_FOCUS_ENTRIES = dedent(
    """
    from __future__ import annotations


    def _login(client):
        response = client.post(
            "/login",
            data={"username": "benbenbuben", "password": "benbenbuben", "next": "/"},
            follow_redirects=False,
        )
        assert response.status_code == 303


    def test_focus_entry_api_roundtrip(client):
        _login(client)
        created = client.post(
            "/api/focus-entries",
            json={"title": "第一条", "body": "先写一条确认记录", "priority": 4},
        )
        assert created.status_code == 201
        payload = created.json()
        assert payload["title"] == "第一条"
        assert payload["priority"] == 4

        listed = client.get("/api/focus-entries")
        assert listed.status_code == 200
        assert listed.json()[0]["title"] == "第一条"
    """
)


def app_files(spec: AppSpec) -> dict[str, str]:
    service_map = {
        "Benprefs": preferences_legacy_data(),
        "Benhealth": health_legacy_data(),
        "Benfinance": finance_legacy_data(),
    }
    files = {
        "AGENTS.md": shared_agents(spec),
        "Makefile": shared_makefile(spec),
        "apps/api/pyproject.toml": shared_pyproject(spec),
        "apps/api/alembic.ini": ALEMBIC_INI if ALEMBIC_INI.endswith("\n") else ALEMBIC_INI + "\n",
        "apps/api/alembic/script.py.mako": ALEMBIC_SCRIPT if ALEMBIC_SCRIPT.endswith("\n") else ALEMBIC_SCRIPT + "\n",
        "apps/api/alembic/env.py": shared_alembic_env(spec),
        "apps/api/alembic/versions/202603080001_initial_focus_entries.py": shared_migration(spec),
        f"apps/api/src/{spec.package}/__init__.py": shared_package_init(),
        f"apps/api/src/{spec.package}/main.py": shared_main(spec),
        f"apps/api/src/{spec.package}/core/__init__.py": shared_package_init(),
        f"apps/api/src/{spec.package}/core/config.py": shared_config(spec),
        f"apps/api/src/{spec.package}/db/__init__.py": shared_package_init(),
        f"apps/api/src/{spec.package}/db/base.py": DB_BASE if DB_BASE.endswith("\n") else DB_BASE + "\n",
        f"apps/api/src/{spec.package}/db/session.py": shared_session(spec),
        f"apps/api/src/{spec.package}/models/__init__.py": MODELS_INIT if MODELS_INIT.endswith("\n") else MODELS_INIT + "\n",
        f"apps/api/src/{spec.package}/models/focus_entry.py": FOCUS_MODEL if FOCUS_MODEL.endswith("\n") else FOCUS_MODEL + "\n",
        f"apps/api/src/{spec.package}/repositories/__init__.py": shared_package_init(),
        f"apps/api/src/{spec.package}/repositories/focus_entries_repo.py": REPO_CODE if REPO_CODE.endswith("\n") else REPO_CODE + "\n",
        f"apps/api/src/{spec.package}/schemas/__init__.py": SCHEMAS_INIT if SCHEMAS_INIT.endswith("\n") else SCHEMAS_INIT + "\n",
        f"apps/api/src/{spec.package}/schemas/focus_entry.py": FOCUS_SCHEMA if FOCUS_SCHEMA.endswith("\n") else FOCUS_SCHEMA + "\n",
        f"apps/api/src/{spec.package}/schemas/dashboard.py": DASHBOARD_SCHEMA if DASHBOARD_SCHEMA.endswith("\n") else DASHBOARD_SCHEMA + "\n",
        f"apps/api/src/{spec.package}/services/__init__.py": shared_package_init(),
        f"apps/api/src/{spec.package}/services/sso.py": shared_sso_service(spec),
        f"apps/api/src/{spec.package}/services/legacy_data.py": service_map[spec.app_dir],
        f"apps/api/src/{spec.package}/api/__init__.py": shared_api_init(),
        f"apps/api/src/{spec.package}/api/router.py": shared_api_router(spec),
        f"apps/api/src/{spec.package}/api/deps.py": shared_api_deps(spec),
        f"apps/api/src/{spec.package}/api/routes/__init__.py": ROUTES_INIT if ROUTES_INIT.endswith("\n") else ROUTES_INIT + "\n",
        f"apps/api/src/{spec.package}/api/routes/system.py": SYSTEM_ROUTE if SYSTEM_ROUTE.endswith("\n") else SYSTEM_ROUTE + "\n",
        f"apps/api/src/{spec.package}/api/routes/dashboard.py": shared_dashboard_route(spec),
        f"apps/api/src/{spec.package}/api/routes/focus_entries.py": shared_focus_entries_route(spec),
        f"apps/api/src/{spec.package}/web/__init__.py": shared_web_init(),
        f"apps/api/src/{spec.package}/web/router.py": shared_web_router(spec),
        f"apps/api/src/{spec.package}/web/templating.py": shared_templating(spec),
        f"apps/api/src/{spec.package}/web/deps.py": WEB_DEPS if WEB_DEPS.endswith("\n") else WEB_DEPS + "\n",
        f"apps/api/src/{spec.package}/web/routes/__init__.py": ROUTES_INIT if ROUTES_INIT.endswith("\n") else ROUTES_INIT + "\n",
        f"apps/api/src/{spec.package}/web/routes/auth.py": shared_auth_routes(spec),
        f"apps/api/src/{spec.package}/web/routes/pages.py": shared_pages_routes(spec),
        "apps/api/tests/conftest.py": render(TESTS_CONFTEST, spec),
        "apps/api/tests/test_health.py": TEST_HEALTH if TEST_HEALTH.endswith("\n") else TEST_HEALTH + "\n",
        "apps/api/tests/test_auth.py": shared_test_auth(spec),
        "apps/api/tests/test_focus_entries_api.py": TEST_FOCUS_ENTRIES if TEST_FOCUS_ENTRIES.endswith("\n") else TEST_FOCUS_ENTRIES + "\n",
        "apps/web/templates/base.html": render(BASE_HTML, spec),
        "apps/web/templates/dashboard.html": DASHBOARD_HTML if DASHBOARD_HTML.endswith("\n") else DASHBOARD_HTML + "\n",
        "apps/web/templates/login.html": render(LOGIN_HTML, spec),
        "apps/web/static/styles.css": STYLES_CSS if STYLES_CSS.endswith("\n") else STYLES_CSS + "\n",
        "data/.gitkeep": "",
        "logs/.gitkeep": "",
    }
    return files


def main() -> None:
    for spec in SPECS:
        root = WORKSPACE_ROOT / spec.app_dir
        for relative_path, content in app_files(spec).items():
            write_file(root / relative_path, content)
        print(spec.app_dir)


if __name__ == "__main__":
    main()
