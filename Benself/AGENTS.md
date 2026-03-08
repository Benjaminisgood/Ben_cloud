# AGENTS.md - Benself

## 当前架构（唯一真实来源）

Benself 已按 Ben_cloud FastAPI 新项目规范搭建，唯一后端代码路径：

- `/Users/ben/Desktop/myapp/Ben_cloud/Benself/apps/api/src/benself_api`

## 目录重点

- API 入口：`apps/api/src/benself_api/main.py`
- JSON/API 路由：`apps/api/src/benself_api/api/routes/`
- Web 路由：`apps/api/src/benself_api/web/routes/`
- 配置：`apps/api/src/benself_api/core/config.py`
- 数据层：`apps/api/src/benself_api/db/`, `.../models/`, `.../repositories/`
- 业务层：`apps/api/src/benself_api/services/`
- 模板：`apps/web/templates/`
- 静态资源：`apps/web/static/`
- 运行数据库：`data/benself.sqlite`
- Graphiti/Kuzu：`data/graphiti.kuzu`
- 日志：`logs/`
- 迁移：`apps/api/alembic/versions/`

## 启动/测试

项目根目录：`/Users/ben/Desktop/myapp/Ben_cloud/Benself`

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

1. 所有后端改动落在 `benself_api` 包内。
2. journal / preferences / health / finance 的读取逻辑必须放在 `services`，不要把跨库 SQL 写进路由层。
3. `graph_sync_runs` 只记录同步运行态；不能把外部源数据库直接当本站可写主库。
4. Graphiti 是 agent 检索层，不是正式业务真相层；正式写入只允许进本站 `data/` 的运行数据库。
5. 先改代码再跑 `make test`；跨应用改动完成后回到工作区根执行 `make test`。
6. 继续迭代时，遵循：
   - `/Users/ben/Desktop/myapp/Ben_cloud/PROJECT_STANDARDS/FASTAPI_ENGINEERING_STANDARD.md`
   - `/Users/ben/Desktop/myapp/Ben_cloud/PROJECT_STANDARDS/FASTAPI_UNIFICATION_PROGRESS.md`
