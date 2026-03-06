# Benlab (FastAPI)

Benlab 已统一为单一后端实现：`FastAPI + SQLAlchemy + Jinja2`。

## 目录结构

```text
Benlab/
├── apps/
│   ├── api/
│   │   ├── alembic/
│   │   │   └── versions/
│   │   ├── src/benlab_api/
│   │   │   ├── api/
│   │   │   ├── core/
│   │   │   ├── db/
│   │   │   ├── models/
│   │   │   ├── repositories/
│   │   │   ├── services/
│   │   │   └── web/
│   │   └── tests/
│   └── web/
│       ├── templates/
│       └── static/
├── data/
│   ├── benlab.sqlite
│   └── uploads/
├── logs/
├── Makefile
└── app.py
```

## 快速开始

```bash
make install
make db-upgrade
make dev
make check
make ci
```

默认地址：
- Web: `http://localhost:9000`
- Health: `http://localhost:9000/health`

## 自动化接入（OpenClaw / Nanobot）

- 指南：`automation/API_AUTOMATION_GUIDE.md`
- 机器索引：`automation/api_index.json`
- Nanobot Action Mapping：`automation/nanobot_action_mapping.json`
- Nanobot 快速上手：`automation/NANOBOT_QUICKSTART.md`
- 全量 OpenAPI：`automation/openapi.json`

刷新 OpenAPI 文件：

```bash
make automation-openapi
```

跑自动化端到端冒烟（需先启动 Benlab）：

```bash
make automation-smoke
```

## 测试

```bash
make test
```

## Alembic

当前 baseline revision：`43cc4d187676`

常用命令：

```bash
make db-current
make db-upgrade
make db-revision m="add_xxx"
```

已有历史数据库（无 `alembic_version`）接管到 Alembic：

```bash
cd apps/api
PYTHONPATH=src alembic stamp 43cc4d187676
PYTHONPATH=src alembic upgrade head
```

## 运行配置

核心环境变量：
- `DATABASE_URL`
- `SECRET_KEY`
- `HOST`
- `PORT`
- `ADMIN_USERNAME`
- `ADMIN_PASSWORD`
- `API_PREFIX`
- `ATTACHMENTS_DIR`
- `LOGS_DIR`
- `DB_BOOTSTRAP_CREATE_ALL`（默认 `false`；仅调试使用）

默认运行路径：
- DB: `data/benlab.sqlite`
- 上传: `data/uploads/`
- 日志: `logs/`

## 说明

- 旧 Flask 单体实现已移除。
- 当前唯一入口：`apps/api/src/benlab_api/main.py`。
- 根目录 `app.py` 为启动脚本，直接调用 `benlab_api.main:run`。
