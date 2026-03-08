
# AGENTS.md - Benprefs

## 当前架构（唯一真实来源）

Benprefs 已按 Ben_cloud FastAPI 新项目规范搭建，唯一后端代码路径：

- `/Users/ben/Desktop/myapp/Ben_cloud/Benprefs/apps/api/src/benprefs_api`

## 目录重点

- API 入口：`apps/api/src/benprefs_api/main.py`
- JSON/API 路由：`apps/api/src/benprefs_api/api/routes/`
- Web 路由：`apps/api/src/benprefs_api/web/routes/`
- 配置：`apps/api/src/benprefs_api/core/config.py`
- 数据层：`apps/api/src/benprefs_api/db/`, `.../models/`, `.../repositories/`
- 业务层：`apps/api/src/benprefs_api/services/`
- 模板：`apps/web/templates/`
- 静态资源：`apps/web/static/`
- 数据库：`data/benprefs.sqlite`
- 日志：`logs/`
- 迁移：`apps/api/alembic/versions/`

## 启动/测试

项目根目录：`/Users/ben/Desktop/myapp/Ben_cloud/Benprefs`

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

1. 所有后端改动落在 `benprefs_api` 包内。
2. 新增查询放 `repositories`，业务逻辑放 `services`，路由层保持薄。
3. 所有展示都以服务层输出的聚合视图为准，不在路由里写复杂 SQL。
4. 先改代码再跑 `make test`；跨应用改动完成后回到工作区根执行 `make test`。
5. 继续迭代时，遵循：
   - `/Users/ben/Desktop/myapp/Ben_cloud/PROJECT_STANDARDS/FASTAPI_ENGINEERING_STANDARD.md`
   - `/Users/ben/Desktop/myapp/Ben_cloud/PROJECT_STANDARDS/FASTAPI_UNIFICATION_PROGRESS.md`
