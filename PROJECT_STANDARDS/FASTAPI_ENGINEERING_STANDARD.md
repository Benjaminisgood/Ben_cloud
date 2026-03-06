# Ben_cloud FastAPI Engineering Standard

本文档是 Ben_cloud **新项目搭建**的工程硬标准。
现有项目改动时可参考，但项目内具体约束以该项目 `AGENTS.md` 为准。

## 1. 适用范围

- 适用于 Ben_cloud 下未来新增的 FastAPI 子项目。
- 新增服务、模块、路由、数据模型必须遵循本规范。

## 2. 标准目录

```text
<project>/
├── apps/
│   ├── api/
│   │   ├── pyproject.toml
│   │   ├── alembic/
│   │   ├── src/<project>_api/
│   │   │   ├── main.py
│   │   │   ├── core/
│   │   │   ├── db/
│   │   │   ├── models/
│   │   │   ├── schemas/
│   │   │   ├── repositories/
│   │   │   ├── services/
│   │   │   ├── api/
│   │   │   ├── web/
│   │   │   └── utils/
│   │   └── tests/
│   └── web/
│       ├── templates/
│       └── static/
├── data/
├── logs/
└── Makefile
```

## 3. 架构分层

- `api/routes`：HTTP 入口层，负责参数解析、鉴权、错误码映射。
- `services`：业务编排层，负责规则、流程、输出组装。
- `repositories`：数据访问层，负责 SQLAlchemy 查询与持久化。
- `models`：ORM 模型定义，按领域拆分文件，不做业务编排。
- `schemas`：Pydantic 数据结构与接口契约。
- `web/routes`：HTML 页面路由，禁止与 API 路由混杂。

约束：
- route 不直接写复杂 SQL。
- repository 不依赖 FastAPI Request/Response。
- service 不直接操作全局会话，统一通过依赖注入传入 `Session`。

## 4. 路由与接口规范

- API 前缀统一由 `api/router.py` 管理（默认 `/api`）。
- 路由文件只声明资源路径，不重复声明 `/api`。
- 命名要求：
  - 列表：`GET /resources`
  - 详情：`GET /resources/{id}`
  - 创建：`POST /resources`
  - 更新：`PATCH /resources/{id}`
  - 删除：`DELETE /resources/{id}`
- 错误返回统一 `{ "detail": "..." }`。

## 5. 配置与运行时

- 统一使用 `core/config.py` + `get_settings()`。
- settings 字段使用全大写。
- 运行期文件统一写入：
  - 数据：`data/`
  - 日志：`logs/`
- 禁止在仓库根目录散落 `*.db`、`*.log`、`*.pid`。

## 6. 数据与迁移

- ORM 基础：`db/base.py`。
- 会话管理：`db/session.py`。
- Schema 变更必须通过 Alembic：
  - `alembic revision --autogenerate`
  - `alembic upgrade head`
- 禁止长期依赖运行时 `create_all` 修补 schema。

## 7. 测试与质量门禁

每个项目最低要求：
- `tests/test_health.py`
- 认证或权限相关测试
- 至少一个领域 API 或 service 测试

CI 最低门禁：
- `python -m compileall src/<project>_api`
- `pytest -q`
- `alembic current`
- 临时库 `alembic upgrade head` 冒烟

## 8. 开发工作流

1. 安装依赖：`make -C <project> install`
2. 本地启动：`make -C <project> dev`
3. 本地检查：`make -C <project> check`
4. 迁移冒烟：`make -C <project> migrate-smoke`
5. 全仓检查：`make ci`

## 9. 变更完成标准（DoD）

一次后端变更必须同时满足：
- 路由、服务、仓储职责边界清晰。
- 新增接口有测试覆盖（至少 1 条成功路径 + 1 条失败路径）。
- 本项目 `check` 通过。
- 根目录 `make ci` 通过。
- 文档或注释补齐对外行为变化。
