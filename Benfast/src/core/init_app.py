import asyncio
from functools import partial
import re

from aerich import Command
from fastapi import FastAPI
from fastapi.middleware import Middleware
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from tortoise.expressions import Q

from api import api_router
from api.v1.base.base import limiter
from core.exceptions import (
    DoesNotExist,
    DoesNotExistHandle,
    HTTPException,
    HttpExcHandle,
    IntegrityError,
    IntegrityHandle,
    RequestValidationError,
    RequestValidationHandle,
    ResponseValidationError,
    ResponseValidationHandle,
    UnhandledExceptionHandle,
)
from core.middlewares import (
    BackGroundTaskMiddleware,
    HttpAuditLogMiddleware,
    RequestLoggingMiddleware,
    SecurityHeadersMiddleware,
)
from log import logger
from models.admin import Api, Menu, Role
from repositories.api import api_repository
from repositories.user import UserCreate, user_repository
from schemas.menus import MenuType
from settings.config import settings
from utils.cache import cache_manager
from utils.password import get_password_hash


def make_middlewares():
    middleware = [
        Middleware(
            CORSMiddleware,
            allow_origins=settings.CORS_ORIGINS_LIST,
            allow_credentials=settings.CORS_ALLOW_CREDENTIALS,
            allow_methods=settings.CORS_ALLOW_METHODS,
            allow_headers=settings.CORS_ALLOW_HEADERS,
        ),
        Middleware(SecurityHeadersMiddleware),  # 安全头中间件
        Middleware(RequestLoggingMiddleware),  # 请求日志中间件
        Middleware(BackGroundTaskMiddleware),
        Middleware(
            HttpAuditLogMiddleware,
            methods=["GET", "POST", "PUT", "DELETE"],
            exclude_paths=[
                "/api/v1/base/access_token",
                "/docs",
                "/openapi.json",
            ],
        ),
    ]
    return middleware


def register_exceptions(app: FastAPI):
    app.add_exception_handler(DoesNotExist, DoesNotExistHandle)
    app.add_exception_handler(HTTPException, HttpExcHandle)
    app.add_exception_handler(IntegrityError, IntegrityHandle)
    app.add_exception_handler(RequestValidationError, RequestValidationHandle)
    app.add_exception_handler(ResponseValidationError, ResponseValidationHandle)
    # 注册通用异常处理器（必须放在最后，作为兜底）
    app.add_exception_handler(Exception, UnhandledExceptionHandle)
    # 注册限流异常处理
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


def register_routers(app: FastAPI, prefix: str = "/api"):
    app.include_router(api_router, prefix=prefix)


async def init_superuser():
    logger.info("🔧 开始初始化超级管理员用户...")
    user = await user_repository.model.exists()
    if not user:
        admin_username = settings.ADMIN_USERNAME.strip() or "benbenbuben"
        admin_password = settings.ADMIN_PASSWORD.strip() or "benbenbuben"
        email_local = re.sub(r"[^a-zA-Z0-9_.+-]", "", admin_username) or "admin"
        await user_repository.model.create(
            username=admin_username,
            email=f"{email_local}@admin.com",
            password=get_password_hash(admin_password),
            is_active=True,
            is_superuser=True,
            dept_id=0,
        )
        logger.info(f"✅ 超级管理员用户创建成功 - 用户名: {admin_username}")
    else:
        logger.info("ℹ️ 超级管理员用户已存在，跳过创建")


async def init_menus():
    logger.info("🔧 开始初始化系统菜单...")
    menus = await Menu.exists()
    if not menus:
        parent_menu = await Menu.create(
            menu_type=MenuType.CATALOG,
            name="系统管理",
            path="/system",
            order=1,
            parent_id=0,
            icon="carbon:gui-management",
            is_hidden=False,
            component="Layout",
            keepalive=False,
            redirect="/system/user",
        )
        children_menu = [
            Menu(
                menu_type=MenuType.MENU,
                name="用户管理",
                path="user",
                order=1,
                parent_id=parent_menu.id,
                icon="material-symbols:person-outline-rounded",
                is_hidden=False,
                component="/system/user",
                keepalive=False,
            ),
            Menu(
                menu_type=MenuType.MENU,
                name="角色管理",
                path="role",
                order=2,
                parent_id=parent_menu.id,
                icon="carbon:user-role",
                is_hidden=False,
                component="/system/role",
                keepalive=False,
            ),
            Menu(
                menu_type=MenuType.MENU,
                name="菜单管理",
                path="menu",
                order=3,
                parent_id=parent_menu.id,
                icon="material-symbols:list-alt-outline",
                is_hidden=False,
                component="/system/menu",
                keepalive=False,
            ),
            Menu(
                menu_type=MenuType.MENU,
                name="API管理",
                path="api",
                order=4,
                parent_id=parent_menu.id,
                icon="ant-design:api-outlined",
                is_hidden=False,
                component="/system/api",
                keepalive=False,
            ),
            Menu(
                menu_type=MenuType.MENU,
                name="部门管理",
                path="dept",
                order=5,
                parent_id=parent_menu.id,
                icon="mingcute:department-line",
                is_hidden=False,
                component="/system/dept",
                keepalive=False,
            ),
            Menu(
                menu_type=MenuType.MENU,
                name="审计日志",
                path="auditlog",
                order=6,
                parent_id=parent_menu.id,
                icon="ph:clipboard-text-bold",
                is_hidden=False,
                component="/system/auditlog",
                keepalive=False,
            ),
        ]
        await Menu.bulk_create(children_menu)
        await Menu.create(
            menu_type=MenuType.MENU,
            name="一级菜单",
            path="/top-menu",
            order=2,
            parent_id=0,
            icon="material-symbols:featured-play-list-outline",
            is_hidden=False,
            component="/top-menu",
            keepalive=False,
            redirect="",
        )
        logger.info("✅ 系统菜单初始化成功 - 菜单数量: 8")
    else:
        logger.info("ℹ️ 系统菜单已存在，跳过初始化")


async def init_apis():
    logger.info("🔧 开始初始化API数据...")
    apis = await api_repository.model.exists()
    if not apis:
        await api_repository.refresh_api()
        api_count = await Api.all().count()
        logger.info(f"✅ API数据初始化成功 - API数量: {api_count}")
    else:
        api_count = await Api.all().count()
        logger.info(f"ℹ️ API数据已存在，跳过初始化 - 当前API数量: {api_count}")


async def init_db():
    command = Command(tortoise_config=settings.TORTOISE_ORM)
    try:
        await command.init_db(safe=True)
    except FileExistsError:
        pass

    await command.init()
    try:
        await command.migrate(no_input=True)
    except AttributeError as e:
        logger.error(f"数据库迁移失败: {e}")
        logger.warning("请手动检查数据库和migrations状态")
        # 不再自动删除migrations文件夹，避免意外丢失迁移历史
        # 如需重置migrations，请手动执行：rm -rf migrations && uv run aerich init-db
        raise RuntimeError("数据库迁移失败，请检查数据库连接和migrations状态") from e

    await command.upgrade(run_in_transaction=True)


async def init_roles():
    logger.info("🔧 开始初始化用户角色...")
    roles = await Role.exists()
    if not roles:
        admin_role = await Role.create(
            name="管理员",
            desc="管理员角色",
        )
        user_role = await Role.create(
            name="普通用户",
            desc="普通用户角色",
        )

        # 分配所有API给管理员角色
        all_apis = await Api.all()
        await admin_role.apis.add(*all_apis)
        # 分配所有菜单给管理员和普通用户
        all_menus = await Menu.all()
        await admin_role.menus.add(*all_menus)
        await user_role.menus.add(*all_menus)

        # 为普通用户分配基本API
        basic_apis = await Api.filter(Q(method__in=["GET"]) | Q(tags="基础模块"))
        await user_role.apis.add(*basic_apis)

        logger.info("✅ 用户角色初始化成功 - 角色: 管理员, 普通用户")
    else:
        role_count = await Role.all().count()
        logger.info(f"ℹ️ 用户角色已存在，跳过初始化 - 当前角色数量: {role_count}")


async def init_data():
    logger.info("🚀 系统初始化开始...")

    logger.info("🔧 开始数据库初始化和迁移...")
    await init_db()
    logger.info("✅ 数据库初始化完成")

    logger.info("🔄 并行初始化基础数据...")
    await asyncio.gather(
        init_superuser(),
        init_menus(),
        init_apis(),
    )
    logger.info("✅ 基础数据初始化完成")

    await init_roles()

    logger.info("🎉 系统初始化完成！")


async def startup():
    """应用启动事件"""
    logger.info("🚀 Fast API应用启动中...")

    # 初始化Redis连接
    await cache_manager.connect()

    # 初始化数据库
    await init_data()


async def shutdown():
    """应用关闭事件"""
    logger.info("🛑 Fast API应用关闭中...")

    # 断开Redis连接
    await cache_manager.disconnect()


async def init_app(app: FastAPI):
    """应用启动时初始化"""
    # 注册启动和关闭事件
    app.add_event_handler("startup", startup)
    app.add_event_handler("shutdown", shutdown)
    logger.info("🎉 Fast API应用启动完成！")


async def stop_app(app: FastAPI):
    """应用关闭时清理"""
    logger.info("🔧 开始停止系统服务...")
    logger.info("👋 系统服务已关闭")


def register_startup_event(app: FastAPI):
    """注册启动和关闭事件"""
    app.add_event_handler("startup", partial(init_app, app))
    app.add_event_handler("shutdown", partial(stop_app, app))
