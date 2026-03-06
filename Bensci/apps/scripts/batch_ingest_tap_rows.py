#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import re
import sys
import tarfile
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from apps.core.config import settings
from apps.db.session import SessionLocal
from apps.services.ingestion_service import ingest_metadata

DEFAULT_CSV = "data/TAP_table_detailed_prompts_v4.csv"
REQUIRED_COLUMNS = ("Level1", "Level2", "Level3", "Prompt")


@dataclass(slots=True)
class SourceRow:
    row_number: int
    level1: str
    level2: str
    level3: str
    prompt: str

    def compact_path(self) -> str:
        return f"{self.level1} > {self.level2} > {self.level3}"

    def save_tags(self) -> list[str]:
        return dedupe_preserve_order([self.level1, self.level2, self.level3])


@dataclass(slots=True)
class SweepTask:
    global_index: int
    row_number: int
    level1: str
    level2: str
    level3: str
    query: str
    save_tags: list[str] = field(default_factory=list)

    def compact_path(self) -> str:
        return f"{self.level1} > {self.level2} > {self.level3}"


@dataclass(slots=True)
class SweepResult:
    global_index: int
    row_number: int
    level1: str
    level2: str
    level3: str
    query: str
    save_tags: list[str]
    status: str
    inserted: int = 0
    updated: int = 0
    skipped: int = 0
    merged_unique: int = 0
    elapsed_seconds: float = 0.0
    attempts: int = 1
    provider_errors: str = ""
    error: str = ""


@dataclass(slots=True)
class RunPaths:
    run_dir: Path
    tasks_dir: Path
    backups_dir: Path
    run_log: Path
    manifest_csv: Path
    manifest_json: Path
    summary_csv: Path
    summary_json: Path


def normalize_text(value: str) -> str:
    return " ".join(str(value or "").replace("\u00a0", " ").split()).strip()


def split_csv_list(raw: str) -> list[str]:
    items: list[str] = []
    for piece in str(raw or "").split(","):
        text = normalize_text(piece)
        if text:
            items.append(text.lower())
    return items


def dedupe_preserve_order(items: list[str]) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for item in items:
        text = normalize_text(item)
        if not text:
            continue
        key = text.casefold()
        if key in seen:
            continue
        seen.add(key)
        result.append(text)
    return result


def slugify(value: str, *, limit: int = 80) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "_", str(value or "").strip()).strip("_").lower()
    if not slug:
        return "item"
    if len(slug) <= limit:
        return slug
    return slug[:limit].rstrip("_") or "item"


def append_line(path: Path, text: str) -> None:
    with path.open("a", encoding="utf-8") as f:
        f.write(text + "\n")


def compact_provider_errors(result) -> str:
    errors: dict[str, list[str]] = {}
    for item in result.provider_stats:
        if item.errors:
            errors[item.provider] = [str(err) for err in item.errors]
    if not errors:
        return ""
    condensed = {provider: " | ".join(messages[:2]) for provider, messages in errors.items()}
    return json.dumps(condensed, ensure_ascii=False)


def archive_run_dir(run_dir: Path, backups_dir: Path) -> Path:
    archive_path = backups_dir / f"{run_dir.name}.tar.gz"
    with tarfile.open(archive_path, "w:gz") as tar:
        tar.add(run_dir, arcname=run_dir.name)
    return archive_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="按 CSV 每一行的 Prompt 抓取 TAP 文献，并一次性追加 Level1/Level2/Level3 三个标签。"
    )
    parser.add_argument(
        "--csv",
        default=DEFAULT_CSV,
        help=f"输入 CSV（默认: {DEFAULT_CSV}）",
    )
    parser.add_argument(
        "--providers",
        default=",".join(settings.default_providers),
        help="provider 列表，逗号分隔；默认使用 settings.default_providers。",
    )
    parser.add_argument(
        "--phases",
        default="",
        help="兼容旧参数，当前已弃用并忽略。",
    )
    parser.add_argument(
        "--start-index",
        type=int,
        default=1,
        help="从第几条任务开始（1-based，基于 CSV 行任务清单）。",
    )
    parser.add_argument(
        "--end-index",
        type=int,
        default=0,
        help="到第几条任务结束（1-based，0 表示直到末尾）。",
    )
    parser.add_argument(
        "--max-results",
        type=int,
        default=50000,
        help="单轮抓取上限。默认 50000。",
    )
    parser.add_argument(
        "--query-filter-mode",
        default="embedding",
        help="query 结果复核模式，可选 none, embedding, boolean, llm。默认 embedding。",
    )
    parser.add_argument(
        "--query-similarity-threshold",
        type=float,
        default=0.35,
        help="query 结果复核阈值，范围 0 到 1。默认 0.35。",
    )
    parser.add_argument(
        "--llm-scoring-prompt",
        default="",
        help="可选，自定义 LLM 逐篇打分提示词。留空时按 query 相关度打分。",
    )
    parser.add_argument(
        "--task-retries",
        type=int,
        default=1,
        help="单轮抓取失败后的额外重试次数。默认 1。",
    )
    parser.add_argument(
        "--retry-sleep-seconds",
        type=float,
        default=0.1,
        help="抓取失败后重试前等待秒数。默认 0.1。",
    )
    parser.add_argument(
        "--sleep-seconds",
        type=float,
        default=0.0,
        help="相邻轮次之间休眠秒数。默认 0。",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="仅生成任务清单与日志，不实际抓取。",
    )
    return parser.parse_args()


def _normalize_header(row: list[str]) -> dict[str, int]:
    mapping: dict[str, int] = {}
    for index, cell in enumerate(row):
        text = normalize_text(cell)
        if text:
            mapping[text.casefold()] = index
    return mapping


def _cell_value(row: list[str], index: int | None) -> str:
    if index is None or index >= len(row):
        return ""
    return normalize_text(row[index])


def load_source_rows(csv_path: Path) -> list[SourceRow]:
    rows: list[SourceRow] = []
    header_map: dict[str, int] | None = None
    data_errors: list[int] = []

    with csv_path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.reader(f)
        for row_number, row in enumerate(reader, start=1):
            normalized_row = [normalize_text(cell) for cell in row]
            if not any(normalized_row):
                continue

            if header_map is None:
                header_map = _normalize_header(row)
                missing = [name for name in REQUIRED_COLUMNS if name.casefold() not in header_map]
                if missing:
                    raise ValueError(f"CSV 表头必须包含 {list(REQUIRED_COLUMNS)}，当前为 {row}")
                continue

            level1 = _cell_value(row, header_map.get("level1"))
            level2 = _cell_value(row, header_map.get("level2"))
            level3 = _cell_value(row, header_map.get("level3"))
            prompt = _cell_value(row, header_map.get("prompt"))
            if not all([level1, level2, level3, prompt]):
                data_errors.append(row_number)
                continue

            rows.append(
                SourceRow(
                    row_number=row_number,
                    level1=level1,
                    level2=level2,
                    level3=level3,
                    prompt=prompt,
                )
            )

    if header_map is None:
        raise RuntimeError(f"CSV 缺少有效表头: {csv_path}")
    if data_errors:
        preview = ", ".join(str(item) for item in data_errors[:10])
        suffix = " ..." if len(data_errors) > 10 else ""
        raise ValueError(f"以下 CSV 行缺少 Level1/Level2/Level3/Prompt，无法执行: {preview}{suffix}")
    if not rows:
        raise RuntimeError(f"未从 CSV 解析出有效任务行: {csv_path}")
    return rows


def build_tasks(rows: list[SourceRow]) -> list[SweepTask]:
    tasks: list[SweepTask] = []
    for global_index, row in enumerate(rows, start=1):
        tasks.append(
            SweepTask(
                global_index=global_index,
                row_number=row.row_number,
                level1=row.level1,
                level2=row.level2,
                level3=row.level3,
                query=row.prompt,
                save_tags=row.save_tags(),
            )
        )
    return tasks


def ensure_run_paths(project_root: Path, run_id: str, *, log_subdir: str = "tap_prompt_ingest") -> RunPaths:
    log_root = project_root / "logs" / log_subdir
    run_dir = log_root / run_id
    tasks_dir = run_dir / "tasks"
    backups_dir = log_root / "backups"

    tasks_dir.mkdir(parents=True, exist_ok=True)
    backups_dir.mkdir(parents=True, exist_ok=True)

    return RunPaths(
        run_dir=run_dir,
        tasks_dir=tasks_dir,
        backups_dir=backups_dir,
        run_log=run_dir / "run.log",
        manifest_csv=run_dir / "manifest.csv",
        manifest_json=run_dir / "manifest.json",
        summary_csv=run_dir / "summary.csv",
        summary_json=run_dir / "summary.json",
    )


def format_tags(tags: list[str]) -> str:
    return json.dumps(tags, ensure_ascii=False)


def task_manifest_row(task: SweepTask) -> dict[str, Any]:
    return {
        "global_index": task.global_index,
        "row_number": task.row_number,
        "level1": task.level1,
        "level2": task.level2,
        "level3": task.level3,
        "path": task.compact_path(),
        "save_tags": format_tags(task.save_tags),
        "query": task.query,
    }


def result_summary_row(result: SweepResult) -> dict[str, Any]:
    payload = asdict(result)
    payload["path"] = f"{result.level1} > {result.level2} > {result.level3}"
    payload["save_tags"] = format_tags(result.save_tags)
    return payload


def write_manifest(paths: RunPaths, tasks: list[SweepTask]) -> None:
    manifest_payload: list[dict[str, Any]] = []
    with paths.manifest_csv.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "global_index",
                "row_number",
                "level1",
                "level2",
                "level3",
                "path",
                "save_tags",
                "query",
            ],
        )
        writer.writeheader()
        for task in tasks:
            row = task_manifest_row(task)
            writer.writerow(row)
            manifest_payload.append(
                {
                    **asdict(task),
                    "path": task.compact_path(),
                }
            )
    paths.manifest_json.write_text(json.dumps(manifest_payload, ensure_ascii=False, indent=2), encoding="utf-8")


def write_summary(paths: RunPaths, results: list[SweepResult]) -> None:
    with paths.summary_csv.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "global_index",
                "row_number",
                "level1",
                "level2",
                "level3",
                "path",
                "save_tags",
                "query",
                "status",
                "inserted",
                "updated",
                "skipped",
                "merged_unique",
                "elapsed_seconds",
                "attempts",
                "provider_errors",
                "error",
            ],
        )
        writer.writeheader()
        for result in results:
            writer.writerow(result_summary_row(result))

    payload = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "total": len(results),
        "ok": sum(1 for item in results if item.status == "ok"),
        "partial_ok": sum(1 for item in results if item.status == "partial_ok"),
        "provider_failed": sum(1 for item in results if item.status == "provider_failed"),
        "no_data": sum(1 for item in results if item.status == "no_data"),
        "error": sum(1 for item in results if item.status == "error"),
        "dry_run": sum(1 for item in results if item.status == "dry_run"),
        "results": [result_summary_row(item) for item in results],
    }
    paths.summary_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def task_log_path(paths: RunPaths, task: SweepTask) -> Path:
    task_name = slugify(f"{task.level1}_{task.level2}_{task.level3}")
    return paths.tasks_dir / f"task_{task.global_index:03d}_row_{task.row_number}_{task_name}.log"


def write_task_header(
    task_log: Path,
    task: SweepTask,
    providers: list[str],
    max_results: int,
    dry_run: bool,
    llm_scoring_prompt: str,
) -> None:
    append_line(task_log, f"global_index={task.global_index}")
    append_line(task_log, f"row_number={task.row_number}")
    append_line(task_log, f"level1={task.level1}")
    append_line(task_log, f"level2={task.level2}")
    append_line(task_log, f"level3={task.level3}")
    append_line(task_log, f"path={task.compact_path()}")
    append_line(task_log, f"save_tags={format_tags(task.save_tags)}")
    append_line(task_log, f"query={task.query}")
    append_line(task_log, f"providers={providers}")
    append_line(task_log, f"max_results={max_results}")
    append_line(task_log, f"dry_run={dry_run}")
    append_line(task_log, f"llm_scoring_prompt={json.dumps(llm_scoring_prompt, ensure_ascii=False)}")


def run_task(
    task: SweepTask,
    *,
    providers: list[str],
    max_results: int,
    query_filter_mode: str,
    query_similarity_threshold: float,
    llm_scoring_prompt: str,
    task_retries: int,
    retry_sleep_seconds: float,
    dry_run: bool,
    paths: RunPaths,
) -> SweepResult:
    task_log = task_log_path(paths, task)
    write_task_header(task_log, task, providers, max_results, dry_run, llm_scoring_prompt)

    header = (
        f"[TASK {task.global_index}] row={task.row_number} path={task.compact_path()!r} "
        f"tags={format_tags(task.save_tags)}"
    )
    append_line(paths.run_log, header)
    print(header, flush=True)

    if dry_run:
        append_line(task_log, "dry_run=true，跳过实际抓取")
        return SweepResult(
            global_index=task.global_index,
            row_number=task.row_number,
            level1=task.level1,
            level2=task.level2,
            level3=task.level3,
            query=task.query,
            save_tags=list(task.save_tags),
            status="dry_run",
        )

    max_attempts = task_retries + 1
    final_result: SweepResult | None = None

    for attempt in range(1, max_attempts + 1):
        begin = time.perf_counter()
        append_line(task_log, f"attempt={attempt}/{max_attempts}")

        def log_callback(message: str) -> None:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            line = f"[{timestamp}] {message}"
            append_line(task_log, line)
            append_line(paths.run_log, f"[task {task.global_index}] {message}")

        session = SessionLocal()
        try:
            ingest_result = ingest_metadata(
                session,
                query=task.query,
                providers=providers,
                max_results=max_results,
                save_tags=task.save_tags,
                query_contexts=task.save_tags,
                query_filter_mode=query_filter_mode,
                query_similarity_threshold=query_similarity_threshold,
                llm_scoring_prompt=llm_scoring_prompt,
                log_callback=log_callback,
            )
            elapsed = round(time.perf_counter() - begin, 3)
            provider_errors = compact_provider_errors(ingest_result)
            provider_failed = bool(provider_errors) and ingest_result.merged_unique == 0
            status = "ok"
            if provider_failed:
                status = "provider_failed"
            elif provider_errors and ingest_result.merged_unique > 0:
                status = "partial_ok"
            elif ingest_result.merged_unique == 0:
                status = "no_data"

            final_result = SweepResult(
                global_index=task.global_index,
                row_number=task.row_number,
                level1=task.level1,
                level2=task.level2,
                level3=task.level3,
                query=task.query,
                save_tags=list(task.save_tags),
                status=status,
                inserted=ingest_result.inserted,
                updated=ingest_result.updated,
                skipped=ingest_result.skipped,
                merged_unique=ingest_result.merged_unique,
                elapsed_seconds=elapsed,
                attempts=attempt,
                provider_errors=provider_errors,
            )

            summary_line = (
                f"[DONE {task.global_index}] status={status} inserted={final_result.inserted} "
                f"updated={final_result.updated} skipped={final_result.skipped} "
                f"merged_unique={final_result.merged_unique} attempts={attempt} elapsed={elapsed}s"
            )
            append_line(paths.run_log, summary_line)
            append_line(task_log, summary_line)
            return final_result
        except Exception as exc:  # pragma: no cover
            session.rollback()
            elapsed = round(time.perf_counter() - begin, 3)
            message = f"{type(exc).__name__}: {exc}"
            final_result = SweepResult(
                global_index=task.global_index,
                row_number=task.row_number,
                level1=task.level1,
                level2=task.level2,
                level3=task.level3,
                query=task.query,
                save_tags=list(task.save_tags),
                status="error",
                elapsed_seconds=elapsed,
                attempts=attempt,
                error=message,
            )
            append_line(task_log, f"[ERROR] {message}")
            append_line(paths.run_log, f"[ERROR {task.global_index}] {message}")
            if attempt < max_attempts:
                append_line(task_log, f"[RETRY] sleep {retry_sleep_seconds}s before retry")
                time.sleep(retry_sleep_seconds)
                continue
            return final_result
        finally:
            session.close()

    return final_result or SweepResult(
        global_index=task.global_index,
        row_number=task.row_number,
        level1=task.level1,
        level2=task.level2,
        level3=task.level3,
        query=task.query,
        save_tags=list(task.save_tags),
        status="error",
        attempts=max_attempts,
        error="unknown_error",
    )


def main() -> int:
    args = parse_args()
    csv_path = Path(args.csv)
    if not csv_path.is_absolute():
        csv_path = PROJECT_ROOT / csv_path
    if not csv_path.exists():
        raise FileNotFoundError(f"CSV 不存在: {csv_path}")

    providers = [item.strip().lower() for item in str(args.providers).split(",") if item.strip()]
    if not providers:
        raise ValueError("providers 不能为空")
    query_filter_mode = normalize_text(args.query_filter_mode).lower() or "embedding"
    if query_filter_mode not in {"none", "embedding", "boolean", "llm"}:
        raise ValueError("query-filter-mode 只能是 none, embedding, boolean, llm")
    query_similarity_threshold = float(args.query_similarity_threshold)
    if not 0 <= query_similarity_threshold <= 1:
        raise ValueError("query-similarity-threshold 必须在 0 到 1 之间")
    llm_scoring_prompt = str(args.llm_scoring_prompt or "").strip()

    rows = load_source_rows(csv_path)
    tasks = build_tasks(rows)
    if not tasks:
        raise RuntimeError("未生成任何任务")

    start_index = max(1, int(args.start_index))
    end_index = int(args.end_index) if int(args.end_index) > 0 else len(tasks)
    if start_index > end_index:
        raise ValueError("start-index 不能大于 end-index")

    selected_tasks = [task for task in tasks if start_index <= task.global_index <= end_index]
    if not selected_tasks:
        raise RuntimeError("按当前 start/end 参数未选中任何任务")

    run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    paths = ensure_run_paths(PROJECT_ROOT, run_id)
    write_manifest(paths, tasks)

    append_line(paths.run_log, f"run_id={run_id}")
    append_line(paths.run_log, f"csv_path={csv_path}")
    append_line(paths.run_log, f"providers={providers}")
    append_line(paths.run_log, f"tasks_total={len(tasks)}")
    append_line(paths.run_log, f"tasks_selected={len(selected_tasks)}")
    append_line(paths.run_log, f"start_index={start_index}")
    append_line(paths.run_log, f"end_index={end_index}")
    append_line(paths.run_log, f"max_results={args.max_results}")
    append_line(paths.run_log, f"query_filter_mode={query_filter_mode}")
    append_line(paths.run_log, f"query_similarity_threshold={query_similarity_threshold}")
    append_line(paths.run_log, f"llm_scoring_prompt={json.dumps(llm_scoring_prompt, ensure_ascii=False)}")
    append_line(paths.run_log, f"task_retries={args.task_retries}")
    append_line(paths.run_log, f"retry_sleep_seconds={args.retry_sleep_seconds}")
    append_line(paths.run_log, f"sleep_seconds={args.sleep_seconds}")
    append_line(paths.run_log, f"dry_run={args.dry_run}")
    append_line(paths.run_log, "note=each_csv_row_uses_prompt_as_query_and_applies_all_three_level_tags")

    ignored_phases = split_csv_list(args.phases)
    if ignored_phases:
        warning = f"[WARN] --phases 已弃用，当前脚本按 CSV 行逐条执行，已忽略: {ignored_phases}"
        append_line(paths.run_log, warning)
        print(warning, flush=True)

    print(f"[INFO] run_id={run_id}")
    print(f"[INFO] manifest={paths.manifest_csv}")
    print(f"[INFO] tasks_total={len(tasks)} selected={len(selected_tasks)} max_results={args.max_results}")
    print(f"[INFO] providers={providers}")
    print(f"[INFO] query_filter_mode={query_filter_mode} threshold={query_similarity_threshold}")
    if llm_scoring_prompt:
        print(f"[INFO] llm_scoring_prompt={llm_scoring_prompt}")
    print(f"[INFO] run_dir={paths.run_dir}")

    results: list[SweepResult] = []

    try:
        for task in selected_tasks:
            result = run_task(
                task,
                providers=providers,
                max_results=args.max_results,
                query_filter_mode=query_filter_mode,
                query_similarity_threshold=query_similarity_threshold,
                llm_scoring_prompt=llm_scoring_prompt,
                task_retries=args.task_retries,
                retry_sleep_seconds=args.retry_sleep_seconds,
                dry_run=args.dry_run,
                paths=paths,
            )
            results.append(result)
            if args.sleep_seconds > 0:
                time.sleep(args.sleep_seconds)
    finally:
        results.sort(key=lambda item: item.global_index)
        write_summary(paths, results)
        archive_path = archive_run_dir(paths.run_dir, paths.backups_dir)
        append_line(paths.run_log, f"manifest_csv={paths.manifest_csv}")
        append_line(paths.run_log, f"manifest_json={paths.manifest_json}")
        append_line(paths.run_log, f"summary_csv={paths.summary_csv}")
        append_line(paths.run_log, f"summary_json={paths.summary_json}")
        append_line(paths.run_log, f"backup_archive={archive_path}")

    print(f"[INFO] summary_csv={paths.summary_csv}")
    print(f"[INFO] summary_json={paths.summary_json}")
    print(f"[INFO] backup_archive={archive_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
