# AGENTS.md - Benusy

## 当前架构（唯一真实来源）

Benusy 已统一为 FastAPI 工程，唯一后端代码路径：

- `/Users/ben/Desktop/Ben_cloud/Benusy/apps/api/src/benusy_api`

## 目录重点

- API 入口：`apps/api/src/benusy_api/main.py`
- Web 路由：`apps/api/src/benusy_api/web/routes/`
- JSON/API 路由：`apps/api/src/benusy_api/api/routes/`
- API 依赖：`apps/api/src/benusy_api/dependencies.py`
- 数据层：`apps/api/src/benusy_api/db/`, `.../models/`, `.../repositories/`
- 业务层：`apps/api/src/benusy_api/services/`
- 模板：`apps/web/templates/`
- 静态资源：`apps/web/static/`
- 数据目录：`data/`
- 迁移：`apps/api/alembic/versions/`

## 启动/测试

项目根目录：`/Users/ben/Desktop/Ben_cloud/Benusy`

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
./benusy.sh install
./benusy.sh start
./benusy.sh status
./benusy.sh stop
```

## 数据库迁移规则（强制）

- 只允许通过 Alembic 变更 schema。
- 禁止在常规流程依赖 runtime `create_all`。
- baseline revision: `43b1d4e82862`。
- 当前 head：`43b1d4e82862`（新增迁移时更新此值）。

## Agent 修改约束

1. 所有后端改动落在 `benusy_api` 包内。
2. 新增查询放 `repositories`，业务逻辑放 `services`，路由层保持薄。
3. 认证依赖（`get_current_user`）同时接受 JWT Bearer 和 session cookie，不要单独拆分两套逻辑。
4. SSO token 验证逻辑不得无故变更——修改会与 Benbot 签名不兼容。
5. 先改代码再跑 `make test`，失败必须修复后再结束。
6. 文档以 `README.md` 与本文件为准。

## 工程规范与持续优化（强制）

1. 新项目开发或既有代码修改，必须遵循：
   - `/Users/ben/Desktop/Ben_cloud/PROJECT_STANDARDS/FASTAPI_ENGINEERING_STANDARD.md`
   - `/Users/ben/Desktop/Ben_cloud/PROJECT_STANDARDS/FASTAPI_UNIFICATION_PROGRESS.md`
2. 不允许为“临时可用”牺牲分层边界（route/service/repository）。
3. 每次交付至少执行一次工程优化动作：
   - 低风险优化直接落地（例如提取重复逻辑、补测试、清理无效代码）。
   - 中高风险优化在交付说明中给出明确下一步清单。
