from __future__ import annotations

import csv
from datetime import datetime
from io import StringIO
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from apps.core.config import settings
from apps.db.session import SessionLocal
from apps.services.article_service import (
    CheckStatus,
    CheckFilterMode,
    SortBy,
    SortOrder,
    TagMode,
    article_to_read_dict,
    list_articles_for_export,
)
from apps.services.task_queue import register_task_handler

EXPORT_ARTICLES_CSV_TASK_TYPE = "export.articles_csv"


class ExportArticlesCsvPayload(BaseModel):
    search: str | None = None
    source: str | None = None
    journal: str | None = None
    tags: str | None = None
    tags_and: str | None = None
    tags_or: str | None = None
    tag_mode: TagMode = "or"
    check_status: str | None = None
    check_filter: CheckFilterMode = "all"
    sort_by: SortBy = "ingested_at"
    sort_order: SortOrder = "desc"
    file_name: str | None = Field(default=None, max_length=256)


def _normalize_check_status(value: str | None) -> CheckStatus | None:
    if not value:
        return None
    candidate = value.strip().lower()
    if candidate in {"unchecked", "correct", "error"}:
        return candidate
    return None


def _sanitize_file_name(raw: str | None) -> str:
    text = (raw or "").strip()
    if not text:
        return ""
    allowed = []
    for ch in text:
        if ch.isalnum() or ch in {"-", "_", "."}:
            allowed.append(ch)
        else:
            allowed.append("_")
    safe = "".join(allowed).strip("._")
    if not safe:
        return ""
    if not safe.lower().endswith(".csv"):
        safe = f"{safe}.csv"
    return safe


def _parse_tags(raw: str | None) -> list[str]:
    if not raw:
        return []
    return [item.strip().lower() for item in raw.split(",") if item.strip()]


def build_articles_csv(
    session: Session,
    *,
    search: str | None,
    source: str | None,
    journal: str | None,
    tags: list[str] | None,
    tags_and: list[str] | None = None,
    tags_or: list[str] | None = None,
    tag_mode: TagMode = "or",
    check_status: str | None = None,
    check_filter: CheckFilterMode = "all",
    sort_by: SortBy = "ingested_at",
    sort_order: SortOrder = "desc",
) -> tuple[str, int]:
    normalized_check_status = _normalize_check_status(check_status)
    articles = list_articles_for_export(
        session,
        search=search,
        source=source,
        journal=journal,
        tags=tags,
        tags_and=tags_and,
        tags_or=tags_or,
        tag_mode=tag_mode,
        check_status=normalized_check_status,
        check_filter=check_filter,
        sort_by=sort_by,
        sort_order=sort_order,
    )

    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(
        [
            "id",
            "doi",
            "title",
            "keywords",
            "abstract",
            "journal",
            "corresponding_author",
            "affiliations",
            "source",
            "publisher",
            "published_date",
            "url",
            "note",
            "check_status",
            "citation_count",
            "impact_factor",
            "ingested_at",
            "tags",
            "created_at",
            "updated_at",
        ]
    )

    for article in articles:
        data = article_to_read_dict(article)
        tag_text = "; ".join(tag_item["name"] for tag_item in data["tags"])
        writer.writerow(
            [
                data["id"],
                data["doi"],
                data["title"],
                "; ".join(data["keywords"]),
                data["abstract"],
                data["journal"],
                data["corresponding_author"],
                "; ".join(data["affiliations"]),
                data["source"],
                data["publisher"],
                data["published_date"],
                data["url"],
                data["note"],
                data["check_status"],
                data["citation_count"],
                data["impact_factor"],
                data["ingested_at"].isoformat() if data.get("ingested_at") else "",
                tag_text,
                data["created_at"].isoformat() if data.get("created_at") else "",
                data["updated_at"].isoformat() if data.get("updated_at") else "",
            ]
        )

    return output.getvalue(), len(articles)


def _write_csv_file(content: str, file_name: str | None = None) -> Path:
    settings.export_dir.mkdir(parents=True, exist_ok=True)
    safe_name = _sanitize_file_name(file_name)
    if not safe_name:
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_name = f"articles_export_{stamp}.csv"

    output_path = settings.export_dir / safe_name
    output_path.write_text(content, encoding="utf-8-sig")
    return output_path


def export_articles_csv_task(payload: dict[str, Any], logger) -> dict[str, Any]:
    request = ExportArticlesCsvPayload.model_validate(payload)
    session = SessionLocal()
    try:
        logger("开始生成 CSV 导出文件...")
        content, total_rows = build_articles_csv(
            session,
            search=request.search,
            source=request.source,
            journal=request.journal,
            tags=_parse_tags(request.tags),
            tags_and=_parse_tags(request.tags_and),
            tags_or=_parse_tags(request.tags_or),
            tag_mode=request.tag_mode,
            check_status=request.check_status,
            check_filter=request.check_filter,
            sort_by=request.sort_by,
            sort_order=request.sort_order,
        )
        output = _write_csv_file(content, file_name=request.file_name)
        logger(f"CSV 导出完成: rows={total_rows}, file={output.name}")
        return {
            "file_name": output.name,
            "file_path": str(output),
            "rows": total_rows,
        }
    finally:
        session.close()


register_task_handler(EXPORT_ARTICLES_CSV_TASK_TYPE, export_articles_csv_task)
