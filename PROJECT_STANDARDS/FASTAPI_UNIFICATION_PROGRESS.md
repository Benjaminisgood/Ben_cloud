# Ben_cloud FastAPI New Project Checklist

本文档是新项目落地时的执行清单，确保新应用从第一天就符合统一规范与最佳实践。

## 1. 初始化阶段

1. 项目目录符合 `FASTAPI_ENGINEERING_STANDARD.md`。
2. `core/config.py` + `get_settings()` 完成，关键配置可由环境变量覆盖。
3. `data/` 与 `logs/` 目录已声明并在运行时自动创建。

## 2. 数据与迁移阶段

1. 创建 Alembic baseline revision。
2. 启动流程不依赖 `create_all` 作为长期 schema 修补方案。
3. 本地与测试都走 `alembic upgrade head`。
4. 提供 `db-upgrade` / `db-current` / `migrate-smoke` 命令。

## 3. 分层与接口阶段

1. `api/routes` 仅做入参校验、鉴权、错误映射。
2. 业务编排在 `services`，数据读写在 `repositories`。
3. 错误返回统一 `{ "detail": "..." }`。
4. 资源型接口遵循 REST 语义（GET/POST/PATCH/DELETE）。

## 4. 质量门禁阶段

1. 至少包含：
   - `tests/test_health.py`
   - 认证/权限测试
   - 至少一条领域 API 或 service 测试
2. 门禁命令可执行：
   - `python -m compileall src/<project>_api`
   - `pytest -q`
   - `alembic current`
   - 临时库 `alembic upgrade head`

## 5. 平台接入阶段（Ben_cloud）

1. 新项目具备 `AGENTS.md`，且说明唯一真实后端路径与约束。
2. 在 `PROJECT_STANDARDS/registry.yaml` 注册项目。
3. 若由 Benbot 承载入口，补充 Benbot `get_projects()` 与 URL 环境变量。
4. 如需 SSO，提供 `/auth/sso` 回调并与共享 `SSO_SECRET` 对齐。

## 6. 交付完成标准

1. 项目可通过 `make install && make db-upgrade && make dev && make test`。
2. 新增接口具备至少 1 条成功路径 + 1 条失败路径测试。
3. 目录无运行时污染物（`*.db/*.log/__pycache__/venv` 不进入仓库）。
4. 文档可支撑下一位开发者在无口头说明下完成继续迭代。
