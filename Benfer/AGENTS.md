# AGENTS.md - Benfer

## 职责定位

Benfer 是 Ben_cloud 的剪贴板与文件中转子应用，核心职责：

1. 文本剪贴板保存与分享（含过期控制）
2. 文件上传中转（含分片上传与类型/大小约束）
3. OSS 对象存储对接
4. Benbot SSO 登录接入（`/auth/sso`）

## 当前架构（唯一真实来源）

唯一后端代码路径：

- `/Users/ben/Desktop/Ben_cloud/Benfer/apps/api/src/benfer_api`

前端静态资源：

- `/Users/ben/Desktop/Ben_cloud/Benfer/apps/web`

## 目录重点

- `apps/api/src/benfer_api/main.py`：FastAPI 应用入口、路由挂载、启动初始化
- `apps/api/src/benfer_api/core/config.py`：服务配置（端口、数据库、OSS、SSO）
- `apps/api/src/benfer_api/api/routes/files.py`：剪贴板/文件 API
- `apps/api/src/benfer_api/api/routes/auth.py`：`/auth/sso` 登录接入
- `apps/api/src/benfer_api/utils/auth.py`：SSO token 校验与 Benfer 本地 session token
- `apps/api/src/benfer_api/services/oss.py`：OSS 上传能力
- `apps/api/src/benfer_api/services/clipboard.py`：剪贴板存储能力
- `apps/api/src/benfer_api/db/database.py`：数据库连接与初始化
- `apps/web/index.html`：前端入口
- `data/`：SQLite 与剪贴板数据目录
- `logs/`：运行日志

## 启动/运维

项目根目录：`/Users/ben/Desktop/Ben_cloud/Benfer`

```bash
./benfer.sh install
./benfer.sh start
./benfer.sh status
./benfer.sh stop
./benfer.sh restart
./benfer.sh logs
./benfer.sh ip
./benfer.sh update
```

端口规则：

- 脚本默认端口为 `8500`
- 若 `.env` 中设置 `PORT`，以 `.env` 为准

## 数据库迁移规则（强制）

1. Schema 变更必须走 Alembic，禁止 ad-hoc 直接改表。
2. 服务启动前通过 `alembic upgrade head` 应用迁移，禁止恢复 `create_all` 作为主路径。
3. 禁止直接 patch 线上数据库文件。

当前 baseline revision：`20260306_0001`（`apps/api/alembic/versions/20260306_0001_baseline_schema.py`）。

## Agent 修改约束

1. 所有后端改动落在 `benfer_api` 包内。
2. 不得无故变更 `utils/auth.py` 中 SSO token 校验算法（会破坏 Benbot 兼容性）。
3. 上传安全边界必须保留：文件大小上限、`content_type` 白名单、分片数量约束。
4. 所有资源读写必须保留用户归属校验（owner check），禁止越权访问。
5. 修改完成后至少执行启动冒烟：`./benfer.sh start` + `GET /health`。
