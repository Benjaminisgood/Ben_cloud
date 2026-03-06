#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Iterable

import requests
from sqlalchemy import select

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from apps.db.models import Article
from apps.db.session import SessionLocal
from apps.services.normalizers import normalize_doi

DEFAULT_CSV = PROJECT_ROOT / "data" / "tapsheets.csv"
SQLITE_IN_CLAUSE_CHUNK_SIZE = 900
TAG_SPLIT_PATTERN = re.compile(r"[;,|，、]")


@dataclass(slots=True)
class InputRow:
    row_number: int
    raw_doi: str
    normalized_doi: str
    row_data: dict[str, str]
    tags: list[str] = field(default_factory=list)


@dataclass(slots=True)
class PendingIngest:
    doi: str
    row_numbers: list[int] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)


@dataclass(slots=True)
class IngestResult:
    doi: str
    ok: bool
    status_code: int | None = None
    article_id: int | None = None
    error: str = ""


def now_text() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def log(message: str) -> None:
    print(f"[{now_text()}] {message}", flush=True)


def parse_csv_list(raw: str) -> list[str]:
    return [item.strip() for item in str(raw or "").split(",") if item.strip()]


def dedupe_keep_order(items: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for item in items:
        text = str(item or "").strip()
        if not text:
            continue
        key = text.lower()
        if key in seen:
            continue
        seen.add(key)
        out.append(text)
    return out


def build_default_existing_output(csv_path: Path) -> Path:
    return csv_path.with_name(f"{csv_path.stem}_existing_in_db.csv")


def build_default_result_output(csv_path: Path, *, ingest_mode: str) -> Path:
    suffix = "quick_ingest_results" if ingest_mode == "quick" else "insert_only_results"
    return csv_path.with_name(f"{csv_path.stem}_{suffix}.csv")


def normalize_header_name(text: str) -> str:
    return str(text or "").strip().casefold()


def resolve_column_name(fieldnames: list[str], requested: str) -> str:
    lookup = {normalize_header_name(name): name for name in fieldnames}
    hit = lookup.get(normalize_header_name(requested))
    if hit:
        return hit
    raise ValueError(f"找不到列 '{requested}'，可选列: {fieldnames}")


def split_tags(text: str) -> list[str]:
    parts = TAG_SPLIT_PATTERN.split(str(text or ""))
    return dedupe_keep_order(parts)


def parse_row_tags(
    row: dict[str, str],
    *,
    static_tags: list[str],
    tag_columns: list[str],
) -> list[str]:
    tags = list(static_tags)
    for col in tag_columns:
        tags.extend(split_tags(row.get(col, "")))
    return dedupe_keep_order(tags)


def read_csv_rows(
    csv_path: Path,
    *,
    doi_column: str,
    static_tags: list[str],
    tag_columns: list[str],
) -> tuple[list[str], list[InputRow], int]:
    with csv_path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        if not reader.fieldnames:
            raise ValueError("CSV 表头为空。")

        fieldnames = [str(name) for name in reader.fieldnames if name is not None]
        resolved_doi_column = resolve_column_name(fieldnames, doi_column)
        resolved_tag_columns = [resolve_column_name(fieldnames, name) for name in tag_columns]

        rows: list[InputRow] = []
        empty_doi_rows = 0
        for row_number, raw_row in enumerate(reader, start=2):
            row_data = {name: str(raw_row.get(name, "") or "").strip() for name in fieldnames}
            raw_doi = row_data.get(resolved_doi_column, "")
            doi = normalize_doi(raw_doi)
            if not doi:
                empty_doi_rows += 1
                continue
            tags = parse_row_tags(
                row_data,
                static_tags=static_tags,
                tag_columns=resolved_tag_columns,
            )
            rows.append(
                InputRow(
                    row_number=row_number,
                    raw_doi=raw_doi,
                    normalized_doi=doi,
                    row_data=row_data,
                    tags=tags,
                )
            )

    return fieldnames, rows, empty_doi_rows


def chunked(items: list[str], size: int) -> Iterable[list[str]]:
    for idx in range(0, len(items), size):
        yield items[idx : idx + size]


def load_existing_article_map(dois: Iterable[str]) -> dict[str, int]:
    doi_list = dedupe_keep_order(dois)
    if not doi_list:
        return {}

    session = SessionLocal()
    try:
        existing: dict[str, int] = {}
        for part in chunked(doi_list, SQLITE_IN_CLAUSE_CHUNK_SIZE):
            stmt = select(Article.doi, Article.id).where(Article.doi.in_(part))
            for doi, article_id in session.execute(stmt).all():
                key = normalize_doi(str(doi or ""))
                if key:
                    existing[key] = int(article_id)
        return existing
    finally:
        session.close()


def classify_rows(
    rows: list[InputRow],
    existing_map: dict[str, int],
) -> tuple[list[tuple[InputRow, int]], list[PendingIngest]]:
    existing_rows: list[tuple[InputRow, int]] = []
    pending_by_doi: dict[str, PendingIngest] = {}

    for row in rows:
        doi = row.normalized_doi
        existing_id = existing_map.get(doi)
        if existing_id is not None:
            existing_rows.append((row, existing_id))
            continue

        task = pending_by_doi.get(doi)
        if task is None:
            pending_by_doi[doi] = PendingIngest(
                doi=doi,
                row_numbers=[row.row_number],
                tags=list(row.tags),
            )
            continue

        task.row_numbers.append(row.row_number)
        task.tags = dedupe_keep_order([*task.tags, *row.tags])

    return existing_rows, list(pending_by_doi.values())


def write_existing_rows_csv(
    output_path: Path,
    *,
    fieldnames: list[str],
    rows: list[tuple[InputRow, int]],
) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    out_fields = ["row_number", *fieldnames, "raw_doi", "normalized_doi", "existing_article_id"]

    with output_path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=out_fields)
        writer.writeheader()
        for item, article_id in rows:
            payload = {"row_number": item.row_number, **item.row_data}
            payload["raw_doi"] = item.raw_doi
            payload["normalized_doi"] = item.normalized_doi
            payload["existing_article_id"] = article_id
            writer.writerow(payload)


def _extract_error_detail(response: requests.Response) -> str:
    try:
        payload = response.json()
    except ValueError:
        text = (response.text or "").strip()
        return text[:400] if text else f"HTTP {response.status_code}"

    if isinstance(payload, dict):
        detail = payload.get("detail")
        if isinstance(detail, str):
            return detail
        if detail is not None:
            return json.dumps(detail, ensure_ascii=False)
        return json.dumps(payload, ensure_ascii=False)
    return str(payload)


def _extract_article_id_from_response_payload(payload: object) -> int | None:
    if not isinstance(payload, dict):
        return None

    article_obj = payload.get("article")
    if isinstance(article_obj, dict):
        value = article_obj.get("id")
    else:
        value = payload.get("id")

    if isinstance(value, int):
        return value
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _lookup_article_id_by_doi(doi: str) -> int | None:
    session = SessionLocal()
    try:
        return session.scalar(select(Article.id).where(Article.doi == doi))
    finally:
        session.close()


def call_ingest_api(
    *,
    api_base_url: str,
    timeout_seconds: float,
    ingest_mode: str,
    include_embedding: bool,
    item: PendingIngest,
) -> IngestResult:
    if ingest_mode == "insert-only":
        endpoint = api_base_url.rstrip("/") + "/articles"
        payload = {
            "doi": item.doi,
            "tags": item.tags,
        }
    else:
        endpoint = api_base_url.rstrip("/") + "/articles/quick"
        payload = {
            "doi": item.doi,
            "tags": item.tags,
            "include_embedding": include_embedding,
        }
    try:
        response = requests.post(endpoint, json=payload, timeout=timeout_seconds)
    except Exception as exc:
        return IngestResult(
            doi=item.doi,
            ok=False,
            status_code=None,
            article_id=None,
            error=f"request_error: {exc}",
        )

    if response.status_code not in (200, 201):
        error_detail = _extract_error_detail(response)
        if ingest_mode == "insert-only" and response.status_code == 400 and "doi 已存在" in error_detail.lower():
            return IngestResult(
                doi=item.doi,
                ok=True,
                status_code=response.status_code,
                article_id=_lookup_article_id_by_doi(item.doi),
                error="already_exists",
            )
        return IngestResult(
            doi=item.doi,
            ok=False,
            status_code=response.status_code,
            article_id=None,
            error=error_detail,
        )

    try:
        response_payload = response.json()
    except ValueError:
        response_payload = {}
    article_id = _extract_article_id_from_response_payload(response_payload)

    return IngestResult(
        doi=item.doi,
        ok=True,
        status_code=response.status_code,
        article_id=article_id,
        error="",
    )


def run_batch_ingest(
    *,
    api_base_url: str,
    timeout_seconds: float,
    ingest_mode: str,
    include_embedding: bool,
    workers: int,
    pending_items: list[PendingIngest],
) -> list[IngestResult]:
    if not pending_items:
        return []

    results: list[IngestResult] = []
    max_workers = max(1, workers)
    total = len(pending_items)
    log(
        "开始调用入库接口: "
        f"mode={ingest_mode}, tasks={total}, workers={max_workers}, include_embedding={include_embedding}"
    )

    if max_workers == 1:
        for idx, item in enumerate(pending_items, start=1):
            result = call_ingest_api(
                api_base_url=api_base_url,
                timeout_seconds=timeout_seconds,
                ingest_mode=ingest_mode,
                include_embedding=include_embedding,
                item=item,
            )
            results.append(result)
            status = "OK" if result.ok else "FAIL"
            log(f"[{idx}/{total}] {status} doi={item.doi}")
        return results

    with ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="quick-ingest") as pool:
        future_map = {
            pool.submit(
                call_ingest_api,
                api_base_url=api_base_url,
                timeout_seconds=timeout_seconds,
                ingest_mode=ingest_mode,
                include_embedding=include_embedding,
                item=item,
            ): item
            for item in pending_items
        }
        done = 0
        for future in as_completed(future_map):
            item = future_map[future]
            done += 1
            try:
                result = future.result()
            except Exception as exc:  # pragma: no cover
                result = IngestResult(doi=item.doi, ok=False, error=f"unexpected_error: {exc}")
            results.append(result)
            status = "OK" if result.ok else "FAIL"
            log(f"[{done}/{total}] {status} doi={item.doi}")

    results.sort(key=lambda item: item.doi)
    return results


def write_ingest_result_csv(
    output_path: Path,
    *,
    ingest_mode: str,
    pending_items: list[PendingIngest],
    results: list[IngestResult],
) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    pending_map = {item.doi: item for item in pending_items}
    fieldnames = ["doi", "ingest_mode", "status", "http_status", "article_id", "error", "row_numbers", "tags"]

    with output_path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for result in results:
            pending = pending_map.get(result.doi)
            writer.writerow(
                {
                    "doi": result.doi,
                    "ingest_mode": ingest_mode,
                    "status": "ok" if result.ok else "failed",
                    "http_status": result.status_code or "",
                    "article_id": result.article_id or "",
                    "error": result.error,
                    "row_numbers": ",".join(str(idx) for idx in (pending.row_numbers if pending else [])),
                    "tags": ",".join(pending.tags if pending else []),
                }
            )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "从 tapsheets CSV 读取 DOI，先和 metadata.db 对比：已存在 DOI 导出到新 CSV；"
            "缺失 DOI 再调用 metadata_service 接口批量录入。"
        )
    )
    parser.add_argument(
        "--csv",
        default=str(DEFAULT_CSV),
        help=f"输入 CSV 路径（默认: {DEFAULT_CSV}）",
    )
    parser.add_argument(
        "--doi-column",
        default="DOI",
        help="DOI 列名（默认: DOI）",
    )
    parser.add_argument(
        "--existing-output",
        default="",
        help="已存在 DOI 输出 CSV 路径；留空时自动写到输入文件同目录。",
    )
    parser.add_argument(
        "--result-output",
        default="",
        help="录入结果输出 CSV 路径；留空时自动写到输入文件同目录。",
    )
    parser.add_argument(
        "--ingest-mode",
        choices=["quick", "insert-only"],
        default="quick",
        help=(
            "录入模式：quick=走 /api/articles/quick（含补全）；"
            "insert-only=走 /api/articles（仅 DOI+标签，不补全）。默认 quick。"
        ),
    )
    parser.add_argument(
        "--api-base-url",
        default="http://127.0.0.1:8080/api",
        help="metadata_service API 基础地址（默认: http://127.0.0.1:8080/api）",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=8,
        help="并发录入线程数（默认: 8）",
    )
    parser.add_argument(
        "--timeout-seconds",
        type=float,
        default=45.0,
        help="单次请求超时时间（秒，默认: 45）",
    )
    parser.add_argument(
        "--tag-columns",
        default="",
        help="可选，逗号分隔的 CSV 列名，作为录入 tags 来源。",
    )
    parser.add_argument(
        "--static-tags",
        default="",
        help="可选，逗号分隔的固定 tags，应用到每个录入请求。",
    )
    parser.add_argument(
        "--include-embedding",
        action="store_true",
        help="仅 quick 模式有效：调用 /api/articles/quick 时启用 embedding 生成。",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=0,
        help="仅录入前 N 个待录入 DOI（0 表示不限）。",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="只做对比和分流，不调用录入接口。",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    csv_path = Path(args.csv).expanduser().resolve()
    if not csv_path.exists():
        raise FileNotFoundError(f"CSV 不存在: {csv_path}")

    existing_output = (
        Path(args.existing_output).expanduser().resolve()
        if args.existing_output
        else build_default_existing_output(csv_path)
    )
    result_output = (
        Path(args.result_output).expanduser().resolve()
        if args.result_output
        else build_default_result_output(csv_path, ingest_mode=args.ingest_mode)
    )

    static_tags = dedupe_keep_order(parse_csv_list(args.static_tags))
    tag_columns = parse_csv_list(args.tag_columns)

    log(f"读取 CSV: {csv_path}")
    fieldnames, rows, empty_doi_rows = read_csv_rows(
        csv_path,
        doi_column=args.doi_column,
        static_tags=static_tags,
        tag_columns=tag_columns,
    )
    unique_dois = dedupe_keep_order([row.normalized_doi for row in rows])
    log(
        "CSV DOI 读取完成: "
        f"rows_with_doi={len(rows)}, unique_doi={len(unique_dois)}, empty_doi_rows={empty_doi_rows}"
    )

    existing_map = load_existing_article_map(unique_dois)
    existing_rows, pending = classify_rows(rows, existing_map)
    pending.sort(key=lambda item: item.doi)

    if args.limit > 0:
        pending = pending[: args.limit]

    write_existing_rows_csv(existing_output, fieldnames=fieldnames, rows=existing_rows)
    log(f"已存在 DOI CSV 已写入: {existing_output} (rows={len(existing_rows)})")
    log(f"待录入 DOI 数: {len(pending)}, ingest_mode={args.ingest_mode}")

    if args.dry_run:
        preview = ", ".join(item.doi for item in pending[:10])
        if preview:
            log(f"dry-run 示例 DOI（前 10 条）: {preview}")
        log("dry-run 完成，未调用录入接口。")
        return 0

    results = run_batch_ingest(
        api_base_url=args.api_base_url,
        timeout_seconds=max(1.0, float(args.timeout_seconds)),
        ingest_mode=args.ingest_mode,
        include_embedding=bool(args.include_embedding),
        workers=max(1, int(args.workers)),
        pending_items=pending,
    )
    write_ingest_result_csv(
        result_output,
        ingest_mode=args.ingest_mode,
        pending_items=pending,
        results=results,
    )
    log(f"录入结果 CSV 已写入: {result_output}")

    ok_count = sum(1 for item in results if item.ok)
    fail_count = len(results) - ok_count
    log(
        "执行完成: "
        f"existing_rows={len(existing_rows)}, pending={len(pending)}, "
        f"ingest_ok={ok_count}, ingest_failed={fail_count}"
    )
    if fail_count:
        log("存在录入失败，请查看结果 CSV 的 error 列。")
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
