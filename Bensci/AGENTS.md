# AGENTS.md - Bensci

## 职责定位

Bensci（CATAPEDIA Metadata Service）是 Ben_cloud 的文献元信息服务，核心职责：

1. 文献元数据抓取、聚合、去重与入库
2. 标签、筛选、检索与导出任务
3. 异步任务队列与补全任务调度
4. Benbot SSO 登录接入（`/auth/sso`）

## 当前架构（唯一真实来源）

唯一后端代码路径：

- `/Users/ben/Desktop/Ben_cloud/Bensci/apps`

## 目录重点

- `apps/main.py`：FastAPI 入口、路由挂载、worker/scheduler 生命周期
- `apps/core/config.py`：配置源（含 SQLite、Provider、SSO、AI 参数）
- `apps/api/router.py`：API 路由聚合
- `apps/api/routers/auth.py`：`/auth/sso` 路由
- `apps/services/sso.py`：SSO token 校验/签发逻辑
- `apps/services/task_queue.py`：异步任务执行
- `apps/services/auto_enrichment_scheduler.py`：自动补全调度
- `apps/db/`：数据库会话与模型
- `apps/api/alembic/versions/`：迁移脚本
- `apps/tests/`：测试目录
- `apps/scripts/`：批处理脚本目录
- `data/`：SQLite 与导出目录
- `logs/`：运行日志

## 启动/运维

项目根目录：`/Users/ben/Desktop/Ben_cloud/Bensci`

```bash
# 首次环境准备
python3 -m venv venv
source venv/bin/activate
cd apps/api
pip install -e ".[dev]"

# 服务运维
cd /Users/ben/Desktop/Ben_cloud/Bensci
./bensci.sh start
./bensci.sh stop
./bensci.sh restart
./bensci.sh status
./bensci.sh logs
```

默认端口：`8300`（可通过 `.env` 中 `PORT` 覆盖）。

## 测试与迁移

测试：

```bash
cd /Users/ben/Desktop/Ben_cloud/Bensci
pytest -q apps/tests
```

迁移：

```bash
cd /Users/ben/Desktop/Ben_cloud/Bensci
cd apps/api
alembic upgrade head
```

## 数据库迁移规则（强制）

1. 新增/变更 schema 必须通过 Alembic revision 管理。
2. 禁止在路由/服务层新增 ad-hoc SQL 改表逻辑。
3. 历史兼容代码中的运行时表结构修复逻辑只用于兜底，不得作为新变更主路径。

## Agent 修改约束

1. 所有后端改动落在 `Bensci/apps` 内，保持 API/service/db 分层。
2. 不得无故变更 `services/sso.py` 的 token 校验算法（需与 Benbot 兼容）。
3. 修改 `task_queue` 或 `auto_enrichment_scheduler` 后，必须验证启动/关闭生命周期可正常收敛。
4. 查询过滤与导出逻辑改动后，必须至少跑对应测试用例。
5. 修改完成后至少执行：`pytest -q apps/tests` 与一次 `GET /health` 冒烟。
