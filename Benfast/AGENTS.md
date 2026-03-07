# AGENTS.md - Benfast

本文件定义 Benfast 在 Ben_cloud 工作区内的执行边界与工程约束。

## 1. 项目定位

Benfast 是 Ben_cloud 的 FastAPI 后端模板子应用，职责是：

1. 作为课题组正式文档站（Markdown -> 文档站模板网页）的主承载应用。
2. 提供可复用的 RBAC / 用户管理后端骨架。
3. 作为 Benbot 门户可跳转的独立子应用（`project_id=benfast`）。
4. 对接 Benbot SSO（`/auth/sso`）实现统一登录。

## 2. 与根级 AGENTS 的关系

执行 Benfast 任务前，必须先读取：

1. `/Users/ben/Desktop/Ben_cloud/AGENTS.md`
2. 本文件

若规则冲突：先遵守根级安全底线，再执行本项目细则。

## 3. 代码与运行范围

- 代码根目录：`/Users/ben/Desktop/Ben_cloud/Benfast`
- 应用入口：`src/__init__.py`
- SSO 路由：`src/sso_routes.py`
- 配置入口：`src/settings/config.py`
- 启停脚本：`benfast.sh`

未明确要求跨应用时，所有改动仅限 Benfast 目录。

## 4. 数据与目录规范（强制）

1. 运行时生成物禁止落在项目根目录。
2. SQLite 文件统一放在 `data/`：
   - `data/benfast.sqlite3`
   - `data/benfast.sqlite3-wal`
   - `data/benfast.sqlite3-shm`
3. 历史根目录 `db.sqlite3*` 视为遗留文件，需迁移到 `data/`。
4. 日志默认在 `logs/`，PID 文件默认在 `logs/benfast.pid`。

## 5. SSO 对接约束（强制）

1. `SSO_SECRET` 必须在 `.env` 显式配置，且与 Benbot 完全一致。
2. 禁止使用弱默认值（例如 `benbot-sso-secret-2025`）。
3. 以下入口必须保持兼容：
   - `GET /health`
   - `GET /auth/sso?token=...`
   - `GET /portal`
4. `verify_sso_token` 的签名算法必须与 Benbot 兼容（Base64URL + HMAC-SHA256）。

## 6. 迁移与数据变更

1. 禁止手工改 SQLite schema。
2. 结构迁移必须遵守根级强制规则（统一走迁移工具流程，不允许 ad-hoc 改表）。
3. 现有 `migrations/` 为历史迁移产物，改动前先评估与 Ben_cloud 统一规则的一致性。
4. 优先改服务层/API，不直接 patch 数据文件。

## 7. 运维命令

```bash
cd /Users/ben/Desktop/Ben_cloud/Benfast
./benfast.sh init-env
./benfast.sh install
./benfast.sh start
./benfast.sh status
./benfast.sh stop
./benfast.sh logs
```

## 8. 测试命令

```bash
cd /Users/ben/Desktop/Ben_cloud/Benfast
make test
make check
```

跨应用改动时，回到根目录执行：

```bash
cd /Users/ben/Desktop/Ben_cloud
make test
```
