#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import sys
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
from apps.scripts.batch_ingest_tap_rows import (
    RunPaths,
    append_line,
    archive_run_dir,
    compact_provider_errors,
    dedupe_preserve_order,
    ensure_run_paths,
    normalize_text,
    slugify,
    split_csv_list,
)

DEFAULT_CSV = "data/TAP_table_detailed_prompts_v4.csv"
DEFAULT_QUERY_PLANNING_DOMAIN_OBJECTIVE = (
    "Focus on literature about Temporal Analysis of Products (TAP) and related transient product analysis methods, "
    "especially their applications in environmental catalysis and energy catalysis. "
    "Prioritize studies that use TAP to analyze catalytic microkinetics, identify elementary reaction steps, "
    "and investigate catalytic mechanisms at molecular or atomic scale. "
    "Keep only papers that are directly relevant to this research direction."
)
LOG_SUBDIR = "tap_all_level_tag_ingest"
LEVEL_COLUMNS = ("Level1", "Level2", "Level3")


@dataclass(slots=True)
class SourceTag:
    first_row_number: int
    tag: str
    source_levels: list[str] = field(default_factory=list)
    occurrence_count: int = 0
    query_contexts: list[str] = field(default_factory=list)


@dataclass(slots=True)
class TagTask:
    global_index: int
    first_row_number: int
    tag: str
    source_levels: list[str]
    occurrence_count: int
    query: str
    query_contexts: list[str] = field(default_factory=list)
    save_tags: list[str] = field(default_factory=list)


@dataclass(slots=True)
class TagSweepResult:
    global_index: int
    first_row_number: int
    tag: str
    source_levels: list[str]
    occurrence_count: int
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


def format_json(value: object) -> str:
    return json.dumps(value, ensure_ascii=False)


def log_line(path: Path, text: str) -> None:
    stamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    append_line(path, f"[{stamp}] {text}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="提取 CSV 的 Level1/Level2/Level3 全部唯一标签，逐个以标签本身为 query 抓取文献，并追加该标签。"
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
        help="从第几条任务开始（1-based，基于去重后的标签任务清单）。",
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
        default="llm",
        help="query 结果复核模式，可选 none, embedding, boolean, llm。默认 llm。",
    )
    parser.add_argument(
        "--query-similarity-threshold",
        type=float,
        default=0.35,
        help="query 结果复核阈值，范围 0 到 1。默认 0.35。",
    )
    parser.add_argument(
        "--query-planning-domain-objective",
        default=DEFAULT_QUERY_PLANNING_DOMAIN_OBJECTIVE,
        help="可选，传给 query planner 的英文目标领域约束。默认聚焦 TAP 在环境催化/能源催化中的微观动力学与机理研究。",
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


def load_unique_tags(csv_path: Path) -> list[SourceTag]:
    unique_tags: dict[str, SourceTag] = {}
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
                missing = [name for name in LEVEL_COLUMNS if name.casefold() not in header_map]
                if missing:
                    raise ValueError(f"CSV 表头必须包含 {list(LEVEL_COLUMNS)}，当前为 {row}")
                continue

            values_by_level: list[tuple[str, str]] = []
            missing_levels: list[str] = []
            for level_name in LEVEL_COLUMNS:
                value = _cell_value(row, header_map.get(level_name.casefold()))
                if value:
                    values_by_level.append((level_name, value))
                else:
                    missing_levels.append(level_name)

            if missing_levels:
                data_errors.append(row_number)
                continue

            for level_name, tag in values_by_level:
                key = tag.casefold()
                current = unique_tags.get(key)
                if current is None:
                    unique_tags[key] = SourceTag(
                        first_row_number=row_number,
                        tag=tag,
                        source_levels=[level_name],
                        occurrence_count=1,
                        query_contexts=[],
                    )
                    continue
                current.occurrence_count += 1
                current.source_levels = dedupe_preserve_order(current.source_levels + [level_name])

    if header_map is None:
        raise RuntimeError(f"CSV 缺少有效表头: {csv_path}")
    if data_errors:
        preview = ", ".join(str(item) for item in data_errors[:10])
        suffix = " ..." if len(data_errors) > 10 else ""
        raise ValueError(f"以下 CSV 行缺少 Level1/Level2/Level3，无法执行: {preview}{suffix}")
    if not unique_tags:
        raise RuntimeError(f"未从 CSV 提取出有效标签: {csv_path}")
    return list(unique_tags.values())


def build_tasks(tags: list[SourceTag]) -> list[TagTask]:
    tasks: list[TagTask] = []
    for global_index, item in enumerate(tags, start=1):
        tasks.append(
            TagTask(
                global_index=global_index,
                first_row_number=item.first_row_number,
                tag=item.tag,
                source_levels=list(item.source_levels),
                occurrence_count=item.occurrence_count,
                query=item.tag,
                query_contexts=list(item.query_contexts),
                save_tags=[item.tag],
            )
        )
    return tasks


def task_manifest_row(task: TagTask) -> dict[str, Any]:
    return {
        "global_index": task.global_index,
        "first_row_number": task.first_row_number,
        "tag": task.tag,
        "source_levels": format_json(task.source_levels),
        "occurrence_count": task.occurrence_count,
        "query_contexts": format_json(task.query_contexts),
        "save_tags": format_json(task.save_tags),
        "query": task.query,
    }


def result_summary_row(result: TagSweepResult) -> dict[str, Any]:
    payload = asdict(result)
    payload["source_levels"] = format_json(result.source_levels)
    payload["save_tags"] = format_json(result.save_tags)
    return payload


def write_manifest(paths: RunPaths, tasks: list[TagTask]) -> None:
    manifest_payload: list[dict[str, Any]] = []
    with paths.manifest_csv.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "global_index",
                "first_row_number",
                "tag",
                "source_levels",
                "occurrence_count",
                "query_contexts",
                "save_tags",
                "query",
            ],
        )
        writer.writeheader()
        for task in tasks:
            row = task_manifest_row(task)
            writer.writerow(row)
            manifest_payload.append(row)
    paths.manifest_json.write_text(json.dumps(manifest_payload, ensure_ascii=False, indent=2), encoding="utf-8")


def write_summary(paths: RunPaths, results: list[TagSweepResult]) -> None:
    with paths.summary_csv.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "global_index",
                "first_row_number",
                "tag",
                "source_levels",
                "occurrence_count",
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


def task_log_path(paths: RunPaths, task: TagTask) -> Path:
    return paths.tasks_dir / f"task_{task.global_index:03d}_row_{task.first_row_number}_{slugify(task.tag)}.log"


def write_task_header(
    task_log: Path,
    task: TagTask,
    providers: list[str],
    max_results: int,
    dry_run: bool,
    query_planning_domain_objective: str,
) -> None:
    log_line(task_log, f"global_index={task.global_index}")
    log_line(task_log, f"first_row_number={task.first_row_number}")
    log_line(task_log, f"tag={task.tag}")
    log_line(task_log, f"source_levels={format_json(task.source_levels)}")
    log_line(task_log, f"occurrence_count={task.occurrence_count}")
    log_line(task_log, f"query_contexts={format_json(task.query_contexts)}")
    log_line(task_log, f"save_tags={format_json(task.save_tags)}")
    log_line(task_log, f"query={task.query}")
    log_line(task_log, f"providers={providers}")
    log_line(task_log, f"max_results={max_results}")
    log_line(task_log, f"dry_run={dry_run}")
    log_line(task_log, f"query_planning_domain_objective={format_json(query_planning_domain_objective)}")


def run_task(
    task: TagTask,
    *,
    providers: list[str],
    max_results: int,
    query_filter_mode: str,
    query_similarity_threshold: float,
    query_planning_domain_objective: str,
    task_retries: int,
    retry_sleep_seconds: float,
    dry_run: bool,
    paths: RunPaths,
) -> TagSweepResult:
    task_log = task_log_path(paths, task)
    write_task_header(
        task_log,
        task,
        providers,
        max_results,
        dry_run,
        query_planning_domain_objective,
    )

    header = (
        f"[TASK {task.global_index}] row={task.first_row_number} tag={task.tag!r} "
        f"source_levels={format_json(task.source_levels)}"
    )
    log_line(paths.run_log, header)
    print(header, flush=True)

    if dry_run:
        log_line(task_log, "dry_run=true，跳过实际抓取")
        return TagSweepResult(
            global_index=task.global_index,
            first_row_number=task.first_row_number,
            tag=task.tag,
            source_levels=list(task.source_levels),
            occurrence_count=task.occurrence_count,
            query=task.query,
            save_tags=list(task.save_tags),
            status="dry_run",
        )

    max_attempts = task_retries + 1
    final_result: TagSweepResult | None = None

    for attempt in range(1, max_attempts + 1):
        begin = time.perf_counter()
        log_line(task_log, f"attempt={attempt}/{max_attempts}")

        def log_callback(message: str) -> None:
            log_line(task_log, message)
            log_line(paths.run_log, f"[task {task.global_index}] {message}")

        session = SessionLocal()
        try:
            ingest_result = ingest_metadata(
                session,
                query=task.query,
                providers=providers,
                max_results=max_results,
                save_tags=task.save_tags,
                query_contexts=task.query_contexts,
                query_planning_domain_objective=query_planning_domain_objective,
                query_filter_mode=query_filter_mode,
                query_similarity_threshold=query_similarity_threshold,
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

            final_result = TagSweepResult(
                global_index=task.global_index,
                first_row_number=task.first_row_number,
                tag=task.tag,
                source_levels=list(task.source_levels),
                occurrence_count=task.occurrence_count,
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
            log_line(paths.run_log, summary_line)
            log_line(task_log, summary_line)
            return final_result
        except Exception as exc:  # pragma: no cover
            session.rollback()
            elapsed = round(time.perf_counter() - begin, 3)
            message = f"{type(exc).__name__}: {exc}"
            final_result = TagSweepResult(
                global_index=task.global_index,
                first_row_number=task.first_row_number,
                tag=task.tag,
                source_levels=list(task.source_levels),
                occurrence_count=task.occurrence_count,
                query=task.query,
                save_tags=list(task.save_tags),
                status="error",
                elapsed_seconds=elapsed,
                attempts=attempt,
                error=message,
            )
            log_line(task_log, f"[ERROR] {message}")
            log_line(paths.run_log, f"[ERROR {task.global_index}] {message}")
            if attempt < max_attempts:
                log_line(task_log, f"[RETRY] sleep {retry_sleep_seconds}s before retry")
                time.sleep(retry_sleep_seconds)
                continue
            return final_result
        finally:
            session.close()

    return final_result or TagSweepResult(
        global_index=task.global_index,
        first_row_number=task.first_row_number,
        tag=task.tag,
        source_levels=list(task.source_levels),
        occurrence_count=task.occurrence_count,
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
    query_filter_mode = normalize_text(args.query_filter_mode).lower() or "llm"
    if query_filter_mode not in {"none", "embedding", "boolean", "llm"}:
        raise ValueError("query-filter-mode 只能是 none, embedding, boolean, llm")
    query_similarity_threshold = float(args.query_similarity_threshold)
    if not 0 <= query_similarity_threshold <= 1:
        raise ValueError("query-similarity-threshold 必须在 0 到 1 之间")
    query_planning_domain_objective = str(args.query_planning_domain_objective or "").strip()

    unique_tags = load_unique_tags(csv_path)
    tasks = build_tasks(unique_tags)
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
    paths = ensure_run_paths(PROJECT_ROOT, run_id, log_subdir=LOG_SUBDIR)
    write_manifest(paths, tasks)

    log_line(paths.run_log, f"run_id={run_id}")
    log_line(paths.run_log, f"csv_path={csv_path}")
    log_line(paths.run_log, f"providers={providers}")
    log_line(paths.run_log, f"tasks_total={len(tasks)}")
    log_line(paths.run_log, f"tasks_selected={len(selected_tasks)}")
    log_line(paths.run_log, f"start_index={start_index}")
    log_line(paths.run_log, f"end_index={end_index}")
    log_line(paths.run_log, f"max_results={args.max_results}")
    log_line(paths.run_log, f"query_filter_mode={query_filter_mode}")
    log_line(paths.run_log, f"query_similarity_threshold={query_similarity_threshold}")
    log_line(paths.run_log, f"query_planning_domain_objective={format_json(query_planning_domain_objective)}")
    log_line(paths.run_log, f"task_retries={args.task_retries}")
    log_line(paths.run_log, f"retry_sleep_seconds={args.retry_sleep_seconds}")
    log_line(paths.run_log, f"sleep_seconds={args.sleep_seconds}")
    log_line(paths.run_log, f"dry_run={args.dry_run}")
    log_line(
        paths.run_log,
        "note=all_unique_labels_use_their_own_label_as_query_and_save_tag_with_explicit_query_planning_constraints",
    )

    ignored_phases = split_csv_list(args.phases)
    if ignored_phases:
        warning = f"[WARN] --phases 已弃用，当前脚本按去重后的标签逐条执行，已忽略: {ignored_phases}"
        log_line(paths.run_log, warning)
        print(warning, flush=True)

    level_counts: dict[str, int] = {level_name: 0 for level_name in LEVEL_COLUMNS}
    for item in unique_tags:
        for level_name in item.source_levels:
            level_counts[level_name] += 1

    print(f"[INFO] run_id={run_id}")
    print(f"[INFO] manifest={paths.manifest_csv}")
    print(f"[INFO] tasks_total={len(tasks)} selected={len(selected_tasks)} max_results={args.max_results}")
    print(f"[INFO] source_level_coverage={level_counts}")
    print(f"[INFO] providers={providers}")
    print(f"[INFO] query_filter_mode={query_filter_mode} threshold={query_similarity_threshold}")
    if query_planning_domain_objective:
        print(f"[INFO] query_planning_domain_objective={query_planning_domain_objective}")
    print(f"[INFO] run_dir={paths.run_dir}")

    results: list[TagSweepResult] = []

    try:
        for task in selected_tasks:
            result = run_task(
                task,
                providers=providers,
                max_results=args.max_results,
                query_filter_mode=query_filter_mode,
                query_similarity_threshold=query_similarity_threshold,
                query_planning_domain_objective=query_planning_domain_objective,
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
        log_line(paths.run_log, f"manifest_csv={paths.manifest_csv}")
        log_line(paths.run_log, f"manifest_json={paths.manifest_json}")
        log_line(paths.run_log, f"summary_csv={paths.summary_csv}")
        log_line(paths.run_log, f"summary_json={paths.summary_json}")
        log_line(paths.run_log, f"backup_archive={archive_path}")

    print(f"[INFO] summary_csv={paths.summary_csv}")
    print(f"[INFO] summary_json={paths.summary_json}")
    print(f"[INFO] backup_archive={archive_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
