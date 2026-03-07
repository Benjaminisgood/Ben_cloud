# Bensci

Bensci 是 Ben_cloud 的文献元信息服务，负责文献抓取、聚合、去重、标签筛选、导出和补全任务调度。

## 核心能力

- 以 DOI 为主键进行去重和多源合并
- 支持 Crossref、OpenAlex、PubMed、Springer、Elsevier、arXiv 等 provider
- 提供检索、标签管理、CSV 导出和异步任务队列
- 支持 Benbot SSO 登录接入
- 支持后台自动补空和 LLM query 复核缓存

## 目录结构

```text
Bensci/
├── app.py
├── bensci.sh
├── Makefile
├── AGENTS.md
├── apps/
│   ├── main.py
│   ├── api/
│   ├── core/
│   ├── db/
│   ├── models/
│   ├── providers/
│   ├── services/
│   ├── scripts/
│   ├── static/
│   └── tests/
├── data/
└── logs/
```

## 快速开始

```bash
cd /Users/ben/Desktop/Ben_cloud/Bensci
python3 -m venv .venv
source .venv/bin/activate
make install
```

复制配置：

```bash
cd /Users/ben/Desktop/Ben_cloud/Bensci
cp .env.example .env
```

开发启动：

```bash
cd /Users/ben/Desktop/Ben_cloud/Bensci
./bensci.sh start
./bensci.sh status
```

默认地址：
- Web: [http://127.0.0.1:8300](http://127.0.0.1:8300)
- Health: [http://127.0.0.1:8300/health](http://127.0.0.1:8300/health)

如果只想本地前台调试，也可以直接运行：

```bash
cd /Users/ben/Desktop/Ben_cloud/Bensci
PYTHONPATH=. .venv/bin/python -m uvicorn apps.main:app --reload --host 0.0.0.0 --port 8300
```

## 测试与迁移

```bash
cd /Users/ben/Desktop/Ben_cloud/Bensci
make test
make check
```

迁移命令：

```bash
cd /Users/ben/Desktop/Ben_cloud/Bensci
cd apps/api
PYTHONPATH=.. alembic upgrade head
```

历史数据库首次接管：

```bash
cd /Users/ben/Desktop/Ben_cloud/Bensci/apps/api
PYTHONPATH=.. alembic stamp head
PYTHONPATH=.. alembic upgrade head
```

## 关键配置

- `PORT`：默认 `8300`
- `SSO_SECRET`：必须与 Benbot 完全一致
- `ALIYUN_AI_API_KEY` / `ALIYUN_AI_MODEL`：AI 补全与复核
- `TASK_WORKER_CONCURRENCY`：后台任务并发数
- `AUTO_ENRICHMENT_*`：自动补空调度参数
- `DEFAULT_PROVIDERS`：默认检索数据源

安全要求：
- 所有密钥必须在 `.env` 显式配置
- 不要在真实环境中使用占位值或弱默认值

## API 概览

- `POST /api/ingestion/fetch`
- `POST /api/ingestion/jobs`
- `GET /api/articles`
- `POST /api/articles/quick`
- `GET /api/articles/export/csv`
- `POST /api/articles/export/jobs/csv`
- `GET /api/tasks`
- `GET /api/enrichment/auto/status`
- `GET /health`

## 更多文档

- 执行边界与修改约束：`/Users/ben/Desktop/Ben_cloud/Bensci/AGENTS.md`
- 批处理脚本说明：`/Users/ben/Desktop/Ben_cloud/Bensci/docs/scripts.md`
