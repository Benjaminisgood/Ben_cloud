# AGENTS.md - Benlab

## 当前架构（唯一真实来源）

Benlab 已统一为 FastAPI 工程，唯一后端代码路径：

- `/Users/ben/Desktop/Ben_cloud/Benlab/apps/api/src/benlab_api`

不再使用 Flask 单体 `app.py` 作为业务实现文件。

## 目录重点

- API 入口：`apps/api/src/benlab_api/main.py`
- Web 路由：`apps/api/src/benlab_api/web/routes/`（`auth.py` + `pages.py` 聚合）
- JSON/API 路由：`apps/api/src/benlab_api/api/`
- 数据层：`apps/api/src/benlab_api/db/`, `.../models/`, `.../repositories/`
- 业务层：`apps/api/src/benlab_api/services/`
- 模板：`apps/web/templates/`
- 静态资源：`apps/web/static/`
- 数据库：`data/benlab.sqlite`
- 运行数据目录：`data/uploads/`
- 日志目录：`logs/`
- 迁移：`apps/api/alembic/versions/`
- 自动化接口资产：`automation/`（`api_index.json`, `nanobot_action_mapping.json`, `openapi.json`）

## 启动/测试

项目根目录：`/Users/ben/Desktop/Ben_cloud/Benlab`

开发：

```bash
make install
make db-upgrade
make dev
```

测试：

```bash
make test
```

脚本运维：

```bash
./benlab.sh install
./benlab.sh start
./benlab.sh status
./benlab.sh stop
```

## 数据库迁移规则（强制）

- 只允许通过 Alembic 变更 schema。
- 禁止在常规流程依赖 runtime `create_all`。
- baseline revision: `43cc4d187676`。

历史库接管：

```bash
cd apps/api
PYTHONPATH=src alembic stamp 43cc4d187676
PYTHONPATH=src alembic upgrade head
```

## Agent 修改约束

1. 所有后端改动落在 `benlab_api` 包内。
2. 新增查询放 `repositories`，业务逻辑放 `services`，路由层保持薄。
3. 先改代码再跑 `make test`，失败必须修复后再结束。
4. 文档以 `readme.md` 与本文件为准，不再引用旧 Flask 描述。

## 工程规范与持续优化（强制）

1. 新项目开发或既有代码修改，必须遵循：
   - `/Users/ben/Desktop/Ben_cloud/PROJECT_STANDARDS/FASTAPI_ENGINEERING_STANDARD.md`
   - `/Users/ben/Desktop/Ben_cloud/PROJECT_STANDARDS/FASTAPI_UNIFICATION_PROGRESS.md`
2. 不允许为“临时可用”牺牲分层边界（route/service/repository）。
3. 每次交付至少执行一次工程优化动作：
   - 低风险优化直接落地（例如提取重复逻辑、补测试、清理无效代码）。
   - 中高风险优化在交付说明中给出明确下一步清单。
