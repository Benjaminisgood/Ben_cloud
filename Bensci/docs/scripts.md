# Bensci Scripts

本文件记录 Bensci 常用批处理脚本的用途、主要参数和输出位置；`README.md` 只保留入口说明。

## 脚本列表

### `apps/scripts/batch_ingest_tap_rows.py`

按 CSV 的 `Prompt` 列逐行构造 query，并批量抓取文献。

常用示例：

```bash
cd /Users/ben/Desktop/Ben_cloud/Bensci
python apps/scripts/batch_ingest_tap_rows.py \
  --csv data/TAP_table_detailed_prompts_v4.csv \
  --providers crossref,openalex,elsevier,pubmed \
  --query-filter-mode llm \
  --query-similarity-threshold 0.35
```

### `apps/scripts/batch_ingest_tap_all_level_tags.py`

读取 CSV 的 `Level1`、`Level2`、`Level3` 三列，按标签去重后逐个检索。每个任务只使用标签本身作为 query，不再混入同一行的 `Prompt` 或其他 level 标签。

行为约定：
- 去重大小写不敏感
- 保留第一次出现时的原始写法和顺序
- 每个唯一标签只跑一次
- 默认用 `llm` 做 query 复核

常用示例：

```bash
cd /Users/ben/Desktop/Ben_cloud/Bensci
python apps/scripts/batch_ingest_tap_all_level_tags.py \
  --csv data/TAP_table_detailed_prompts_v4.csv \
  --providers crossref,openalex,elsevier,pubmed \
  --query-filter-mode llm \
  --query-similarity-threshold 0.35
```

后台执行：

```bash
cd /Users/ben/Desktop/Ben_cloud/Bensci
nohup python apps/scripts/batch_ingest_tap_all_level_tags.py \
  --csv data/TAP_table_detailed_prompts_v4.csv \
  --providers crossref,openalex,elsevier,pubmed \
  --query-filter-mode llm \
  --query-similarity-threshold 0.35 \
  > /tmp/tap_all_level_tag_ingest.out 2>&1 &
```

## 关键参数

- `--csv`：输入 CSV 路径
- `--providers`：数据源列表
- `--query-filter-mode`：`none`、`boolean`、`embedding`、`llm`
- `--query-similarity-threshold`：相关度阈值
- `--query-planning-domain-objective`：英文研究目标约束
- `--start-index` / `--end-index`：按去重后的任务序号截取
- `--dry-run`：只生成任务清单和日志，不执行抓取

## 输出位置

- `logs/tap_prompt_ingest/<run_id>/`
- `logs/tap_all_level_tag_ingest/<run_id>/`

重点文件：
- `run.log`
- `summary.csv`
- `summary.json`

## 兼容脚本

`apps/scripts/batch_ingest_tap_level3_tags.py` 当前兼容转发到 `batch_ingest_tap_all_level_tags.py`。
