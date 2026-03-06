# Benoss (Web Only)

Benoss 是单一 Web 形态项目：`FastAPI + Jinja2 + Vanilla JS`。

## 项目结构

```text
.
├── apps/
│   ├── api/                    # FastAPI 后端
│   │   └── src/benoss_api/
│   │       ├── main.py         # app factory + lifespan
│   │       ├── core/           # 配置
│   │       ├── db/             # SQLAlchemy session
│   │       ├── api/            # API 路由
│   │       ├── web/            # 页面路由 + 页面依赖/flash
│   │       ├── models/         # ORM 模型
│   │       ├── repositories/   # 数据访问层
│   │       ├── services/       # 业务服务层
│   │       └── utils/          # 工具函数
│   └── web/                    # 模板和静态资源
├── data/                       # 本地数据目录
├── logs/                       # 运行日志
├── app.py                      # 根目录启动脚本（调用 benoss_api.main:run）
└── benoss.sh                   # 启停脚本
```

## 快速开始

```bash
make install
make db-upgrade
make dev
make check
make ci
make test
```

统一运维脚本：

```bash
./benoss.sh install
./benoss.sh start
./benoss.sh status
./benoss.sh logs
```

数据库迁移（Alembic）：

```bash
make db-current
make db-revision m="init_schema"
make db-upgrade
```

已有历史库（无 `alembic_version`）迁移到 Alembic 管理：

```bash
cd apps/api
PYTHONPATH=src alembic stamp e2b74479111a
PYTHONPATH=src alembic upgrade head
```

配置文件使用仓库根目录 `.env`（基于 `.env.example` 创建）。

默认采用迁移优先启动，不再在应用启动时隐式 `create_all`。如需临时兼容旧流程，可设置 `DB_BOOTSTRAP_CREATE_ALL=true`。
默认会在应用启动时自动执行 `alembic upgrade head`（仅在库未初始化或版本落后时触发）。如需关闭，可设置 `DB_AUTO_UPGRADE_ON_STARTUP=false`。

说明：
- 唯一业务入口仍是 `apps/api/src/benoss_api/main.py`。
- 根目录 `app.py` 仅作为启动转发脚本，保持与 Benlab 一致的目录约定。

访问：
- Web: `http://localhost:8000`
- Swagger: `http://localhost:8000/docs`

## 自动化接入（OpenClaw / Nanobot）

- 指南：`automation/API_AUTOMATION_GUIDE.md`
- 机器索引：`automation/api_index.json`
- Nanobot Action Mapping：`automation/nanobot_action_mapping.json`
- Nanobot 快速上手：`automation/NANOBOT_QUICKSTART.md`
- 全量 OpenAPI：`automation/openapi.json`
