# CATAPEDIA Metadata Service

独立于 Bensci 的 FastAPI 子项目，负责文献元数据提取、聚合、去重、入库与管理。

## 目标

- 以 DOI 作为唯一去重依据（SQLite 唯一约束 + 多源合并）。
- 面向化学/TAP/催化/能源文献，支持多数据源聚合。
- 元数据字段覆盖：DOI、标题、关键词、摘要、期刊、通讯作者、机构院校等。
- 支持核查状态管理：`未检查 / 正确 / 错误`。
- 文献列表支持按 `最近录入/更新时间 / 发表时间 / 影响因子` 排序。
- 内置 FTS5 全文索引（标题/摘要/关键词/作者/机构等字段）。
- 持久化任务队列（SQLite `tasks`）+ 日志增量轮询。
- 支持文献批量导出 CSV（同步下载 + 异步任务导出）。
- 快速录入只需 `DOI + 标签`，系统会先走 DOI 元数据补全，再用 AI 兜底补空。
- “补全所有空格子”由后台自动守护进程周期执行，无需前端手动触发。
- 提供前端完成标签管理、筛选、检索、录入、删除、编辑。
- Provider 插件化，便于后续扩展更多接口源。

## 目录结构

```text
Bensci/
  apps/
    api/                 # FastAPI 路由层 + Alembic 迁移
      alembic/
      alembic.ini
      pyproject.toml
    core/                # 配置
    db/                  # SQLAlchemy 模型与会话
    models/              # Pydantic Schema
    providers/           # 元数据来源插件（Crossref/OpenAlex/PubMed/...）
    services/            # 业务逻辑（聚合、upsert、筛选）
    static/              # 前端页面（HTML/JS/CSS）
    main.py
    scripts/
    tests/
  data/                  # 运行态数据（SQLite/CSV/导出文件）
    exports/
  logs/                  # 服务与批处理日志
  .env
```

## 快速启动

```bash
cd /Users/ben/Desktop/Ben_cloud/Bensci
python3 -m venv .venv
source .venv/bin/activate
cd apps/api
pip install -e ".[dev]"
```

```bash
# cp .env.example .env
```

```bash
uvicorn apps.main:app --reload --port 8080
```

打开：`http://127.0.0.1:8080`

## Alembic 迁移

```bash
cd /Users/ben/Desktop/Ben_cloud/Bensci
cd apps/api
alembic upgrade head
```

常用命令：

```bash
cd /Users/ben/Desktop/Ben_cloud/Bensci/apps/api
alembic revision -m "your message"
alembic upgrade head
alembic downgrade -1
```

如果你已经有历史 `metadata.db`（表已存在但未纳入 Alembic），先执行一次：

```bash
cd /Users/ben/Desktop/Ben_cloud/Bensci/apps/api
alembic stamp head
```

然后再使用 `alembic upgrade head` 进行后续迁移。

## API 概览

- `POST /api/ingestion/fetch`：多源拉取并写入 SQLite。
- `POST /api/ingestion/jobs`：创建异步拉取任务（返回 `job_id`）。
- `GET /api/ingestion/jobs/{job_id}`：读取任务状态和增量日志。
- `GET /api/providers`：查看数据源是否已配置。
- `GET /api/articles`：检索/筛选文献（支持 `tags=tag1,tag2` + `tag_mode=or|and` 多标签逻辑）。
- `GET /api/articles?sort_by=ingested_at|published_date|impact_factor&sort_order=desc|asc`：排序查询。
- `GET /api/articles/export/csv`：按当前筛选导出 CSV（直接下载，支持多标签筛选参数）。
- `POST /api/articles/export/jobs/csv`：创建异步 CSV 导出任务。
- `POST /api/articles/quick`：仅 DOI+标签录入并立刻同步补全（先元数据聚合，再 AI 阅读，不排队）。
- `POST /api/enrichment/jobs/fill-empty`：手动创建批量补空任务（保留 API 调用能力）。
- `POST /api/enrichment/jobs/article/{id}`：触发单篇补全任务。
- `GET /api/enrichment/jobs/{job_id}`：查询补全任务状态与日志。
- `POST /api/enrichment/jobs/{job_id}/pause|resume|cancel`：暂停/继续/停止补全任务。
- `GET /api/enrichment/auto/status`：后台自动补空任务状态与增量日志。
- `POST /api/enrichment/auto/enabled`：开启/关闭后台自动补空守护任务（运行时开关；关闭时会对当前 auto 任务发送停止请求）。
- `POST /api/tasks`：创建通用任务（可扩展更多 task_type）。
- `GET /api/tasks`：按状态/类型分页查看任务。
- `GET /api/tasks/{task_id}`：查看任务详情和增量日志。
- `GET /api/tasks/{task_id}/download`：下载任务产物（如 CSV 导出文件）。
- `POST /api/articles`：手动录入。
- `GET /api/articles/query-filter/dropped`：查看当前 SQLite 中被 LLM drop 的 DOI 缓存及原因。
- `POST /api/articles/query-filter/dropped/{entry_id}/rescue`：把一条 drop 缓存手动救回到 keep 缓存。
- `PUT /api/articles/{id}`：编辑。
- `DELETE /api/articles/{id}`：删除。
- `PUT /api/articles/{id}/tags`：手动加标签。
- `GET /api/tags?include_counts=true`：标签列表（可返回每个标签对应文献数量）。

说明：
- ingestion 请求使用 `query` 字段（可填自然语言或标准检索式）。系统会先尝试 AI 解析并翻译到各 provider 语法，失败时自动回退为原词直接检索。
- Web 前端的 `llm` 复核默认按当前 `query` 及其解析出的检索意图判断相关度，不再额外读取单独的领域提示词配置。

## Provider 扩展方式

1. 在 `apps/providers/` 下新增 provider 文件，实现：
   - `key/title/description`
   - `is_configured()`
   - `search(query, max_results) -> list[ProviderRecord]`
2. 在 `apps/providers/registry.py` 注册。
3. 前端会自动读取 `/api/providers` 显示。

## 说明

- Springer/Elsevier 需要 API key，未配置时会自动跳过。
- DOI 为空的记录会被跳过，避免污染主库去重逻辑。
- `metadata.db` 默认生成在 `data/metadata.db`。
- 拉取支持高级约束：query 结果复核模式（`none` / `boolean` / `llm` / `embedding占位`，当前默认 `llm`）、发布时间范围、关键词约束、期刊白名单/黑名单、最少被引次数。
- 文章影响因子过滤只判断文章记录本身的 `impact_factor` 字段，不再按期刊 CSV 回填。
- AI 配置通过 `.env`：`ALIYUN_AI_API_KEY`、`ALIYUN_AI_API_BASE_URL`、`ALIYUN_AI_MODEL`。
- LLM query 复核的备用模型通过 `.env` 配置：
  - `QUERY_FILTER_LLM_FALLBACK_MODELS`：逗号分隔的备用模型列表，主模型失败时自动切换
- LLM query 复核会把 DOI 判定结果缓存到 SQLite 的 `llm_query_filter_kept` / `llm_query_filter_dropped` 两张表；相同判定范围下再次遇到同一 DOI 时会直接复用，不再重复调用模型。
- 前端“查看 Drop 文献”按钮会读取 `llm_query_filter_dropped` 中的缓存记录，并支持手动“救回”；救回后该 DOI 在相同判定范围下会直接视为 keep，不再被同一条 drop 缓存拦截。
- 任务队列相关配置：
  - `TASK_WORKER_CONCURRENCY`：后台任务并发 worker 数（默认 2）
  - `TASK_POLL_INTERVAL_SECONDS`：队列轮询间隔（默认 0.5）
  - `EXPORT_DIR`：CSV 导出目录（默认 `data/exports`）
- 后台自动补空配置：
  - `AUTO_ENRICHMENT_ENABLED`：是否启用后台自动补空（默认 true）
  - `AUTO_ENRICHMENT_INTERVAL_SECONDS`：自动补空轮询间隔秒数（默认 180）
  - `AUTO_ENRICHMENT_LIMIT`：单次自动补空扫描上限（默认 100）
  - `AUTO_ENRICHMENT_WORKERS`：单次自动补空并发线程数（默认 4）

```bash
cd /Users/ben/Desktop/Ben_cloud/Bensci

python apps/scripts/batch_ingest_tap_rows.py \
  --csv data/TAP_table_detailed_prompts_v4.csv \
  --providers crossref,openalex,elsevier,pubmed \
  --query-filter-mode llm \
  --query-similarity-threshold 0.35

python apps/scripts/batch_ingest_tap_all_level_tags.py \
  --csv data/TAP_table_detailed_prompts_v4.csv \
  --providers crossref,openalex,elsevier,pubmed \
  --query-filter-mode llm \
  --query-similarity-threshold 0.35

nohup python apps/scripts/batch_ingest_tap_rows.py \
  --csv data/TAP_table_detailed_prompts_v4.csv \
  --providers crossref,openalex,elsevier,pubmed \
  --query-filter-mode llm \
  --query-similarity-threshold 0.35 \
  > /tmp/tap_prompt_ingest.out 2>&1 &

nohup python apps/scripts/batch_ingest_tap_all_level_tags.py \
  --csv data/TAP_table_detailed_prompts_v4.csv \
  --providers crossref,openalex,elsevier,pubmed \
  --query-filter-mode llm \
  --query-similarity-threshold 0.35 \
  > /tmp/tap_all_level_tag_ingest.out 2>&1 &

python apps/scripts/batch_ingest_tap_all_level_tags.py \
  --csv data/TAP_table_detailed_prompts_v4.csv \
  --providers elsevier \
  --query-filter-mode llm \
  --query-similarity-threshold 0.35 \
  --start-index 1 \
  --end-index 0

ps -ef | grep batch_ingest_tap_all_level_tags.py
ben   12345  ... python apps/scripts/batch_ingest_tap_all_level_tags.py ...
kill 12345
kill -9 12345
pkill -f batch_ingest_tap_all_level_tags.py
pgrep -af batch_ingest_tap_all_level_tags.py
tail -f /tmp/tap_all_level_tag_ingest.out
```

`batch_ingest_tap_rows.py` 会按 CSV 的 `Prompt` 逐行检索；`batch_ingest_tap_all_level_tags.py` 会提取 `Level1` / `Level2` / `Level3` 三列里所有出现过的标签，去重后逐个以标签本身作为 query 检索。每个任务只会追加当前这个标签本身，也不会再把同一行的 `Prompt`、其他 level 标签混入 query context。`all_level_tags` 支持显式的 query planning 领域约束，但现在只保留一段英文自然语言 `domain objective`，不再额外传结构化 scope profile。LLM 逐篇复核默认按 `query + domain objective` 的相关度打分，不再区分自定义评分 prompt。

`batch_ingest_tap_all_level_tags.py` 的 `run.log` 和各 task 日志现在每一行都带时间戳；在 `llm` 模式下会逐篇输出 DOI、keep/drop、原因、使用模型以及 prompt/completion/total token，用于观察实时进度和 token 消耗。

兼容入口 `apps/scripts/batch_ingest_tap_level3_tags.py` 现在也会转到这个全量标签脚本。

运行后日志会在 `logs/tap_prompt_ingest/<run_id>/` 或 `logs/tap_all_level_tag_ingest/<run_id>/` 下面，重点看 `run.log`、`summary.csv`、`summary.json`。


# 新脚本逻辑

读取 CSV 的 Level1、Level2、Level3 三列；`Prompt` 列即使存在，也不会参与这个脚本的检索上下文构造。
把这三列里所有出现过的标签全部收集起来。
对所有标签做去重。
去重是大小写不敏感的。
保留第一次出现时的原始写法和顺序。
每个唯一标签生成一个独立任务。
每个任务的检索词只用这个标签本身。
例如标签是 CeO2，query 就只有 CeO2。
不会再把同一行的 Prompt、Level1、Level2、Level3 其他词作为隐式扩展条件传给 query planner。
默认会把一段固定的研究目标领域约束传给 query planner：
Focus on literature about Temporal Analysis of Products (TAP) and related transient product analysis methods, especially their applications in environmental catalysis and energy catalysis. Prioritize studies that use TAP to analyze catalytic microkinetics, identify elementary reaction steps, and investigate catalytic mechanisms at molecular or atomic scale. Keep only papers that are directly relevant to this research direction.
每个任务入库时也只追加这个标签本身。
不会再自动把同一行的三级标签一起打上。
默认用 llm 做二次复核，按当前 query 及其解析出的领域约束判断相关度。
LLM 分数高于阈值的结果保留，低于阈值的丢掉。
每个任务都会单独写日志、汇总结果和归档。
这意味着什么

同一个标签如果在很多行里重复出现，只会跑一次。
同一个词如果既出现在 Level2 又出现在 Level3，也只会跑一次。
任务清单里会记录：
这个标签第一次出现在哪一行
它出现过几次
它来自哪些 level
关键参数

--csv
输入 CSV，默认 data/TAP_table_detailed_prompts_v4.csv
--providers
数据源列表
--query-filter-mode
可选 none / embedding / boolean / llm
默认是 llm
--query-similarity-threshold
阈值，默认 0.35
--query-planning-domain-objective
传给 query planner 的英文自然语言目标领域约束
默认是 TAP 在环境催化/能源催化中的微观动力学与机理研究方向
--start-index / --end-index
按“去重后的任务序号”截取运行范围，不是按原 CSV 行号
--dry-run
只生成任务清单和日志，不实际抓取
输出位置
日志和结果会在：

/Users/ben/Desktop/Ben_cloud/Bensci/logs/tap_all_level_tag_ingest/<run_id>/

重点看：

run.log
manifest.csv
manifest.json
summary.csv
summary.json

# 旧脚本逻辑
旧脚本是 batch_ingest_tap_rows.py (line 149)。

它的核心逻辑是“按 CSV 每一行跑一次”：

读取 CSV，要求每行必须有 Level1、Level2、Level3、Prompt，见 load_source_rows。
每一行生成一个任务，不做跨行标签去重，见 build_tasks。
这个任务的检索词不是标签，而是这一行的 Prompt。
这个任务入库时会给命中的文献同时追加这行的三个标签：Level1 + Level2 + Level3。
然后调用 ingest_metadata(...) 去抓 provider 数据、按 DOI 聚合、做 query 复核、再 upsert 入库，见 run_task。
所以旧脚本的本质是：

一行 = 一个独立检索任务
query = Prompt
save_tags = [Level1, Level2, Level3]
不对重复标签做去重
这会带来几个直接后果：

如果同一个 Level3 在不同 CSV 行里出现 5 次，旧脚本会跑 5 次。
即使两个任务的核心标签一样，只要 Prompt 不同，它也会当成两个独立检索任务。
同一篇文献可能被多次命中，但最终数据库层会按 DOI 去重，只是会重复经历抓取和更新流程。
日志目录也和新脚本不同，旧脚本写到：

logs/tap_prompt_ingest/<run_id>/

而且它自己在日志里也明确写了这条语义，见 main：
each_csv_row_uses_prompt_as_query_and_applies_all_three_level_tags
