from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from apps.api.deps import get_db
from apps.db.models import Article
from apps.db import rebuild_fts_index
from apps.models.schemas import (
    ArticleCreate,
    ArticleListResponse,
    ArticleRead,
    ArticleTagUpdate,
    ArticleUpdate,
    DroppedQueryFilterDecisionListResponse,
    DroppedQueryFilterDecisionRead,
    DroppedQueryFilterRescueResponse,
    QuickArticleCreate,
    QuickArticleCreateResponse,
    TagMatchMode,
    TaskCreateResponse,
)
from apps.services.ai_enrichment import enrich_article_by_id
from apps.services.normalizers import normalize_doi
from apps.services.article_service import (
    CheckFilterMode,
    SortBy,
    SortOrder,
    article_to_read_dict,
    create_article,
    delete_article,
    get_article_or_none,
    list_articles,
    update_article,
)
from apps.services.export_service import EXPORT_ARTICLES_CSV_TASK_TYPE, ExportArticlesCsvPayload, build_articles_csv
from apps.services.query_filter_cache_service import list_dropped_query_filter_entries, rescue_dropped_query_filter_entry
from apps.services.task_queue import enqueue_task

router = APIRouter(prefix="/articles", tags=["articles"])


def _to_read(article) -> ArticleRead:
    return ArticleRead.model_validate(article_to_read_dict(article))


def _append_local_log(logs: list[str], message: str) -> None:
    stamp = datetime.now().strftime("%H:%M:%S")
    logs.append(f"[{stamp}] {message}")


def _parse_tags(raw: str | None) -> list[str]:
    if not raw:
        return []
    items = [item.strip().lower() for item in raw.split(",")]
    return [item for item in items if item]


def _normalize_tag_list(tags: list[str]) -> list[str]:
    seen: set[str] = set()
    normalized: list[str] = []
    for raw in tags:
        name = str(raw).strip().lower()
        if not name or name in seen:
            continue
        seen.add(name)
        normalized.append(name)
    return normalized


def _merge_note_text(existing_note: str, incoming_note: str) -> str:
    old_text = str(existing_note or "").strip()
    new_text = str(incoming_note or "").strip()
    if not new_text:
        return old_text
    if not old_text:
        return new_text
    old_lines = {line.strip() for line in old_text.splitlines() if line.strip()}
    new_lines = [line.strip() for line in new_text.splitlines() if line.strip()]
    append_lines = [line for line in new_lines if line not in old_lines]
    if not append_lines:
        return old_text
    append_text = "\n".join(append_lines)
    return f"{old_text}\n\n{append_text}"


@router.get("", response_model=ArticleListResponse)
def get_articles(
    search: str | None = Query(default=None, description="全文检索关键词"),
    source: str | None = Query(default=None),
    journal: str | None = Query(default=None),
    tags: str | None = Query(default=None, description="逗号分隔，多标签筛选"),
    tags_and: str | None = Query(default=None, description="逗号分隔，AND 标签筛选"),
    tags_or: str | None = Query(default=None, description="逗号分隔，OR 标签筛选"),
    tag_mode: TagMatchMode = Query(default="or"),
    check_status: str | None = Query(default=None),
    check_filter: CheckFilterMode = Query(default="all"),
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
    sort_by: SortBy = Query(default="ingested_at"),
    sort_order: SortOrder = Query(default="desc"),
    db: Session = Depends(get_db),
) -> ArticleListResponse:
    normalized_check_status = None
    if check_status:
        candidate = check_status.strip().lower()
        if candidate not in {"unchecked", "correct", "error"}:
            raise HTTPException(status_code=400, detail="check_status 必须是 unchecked/correct/error")
        normalized_check_status = candidate

    selected_tags = _parse_tags(tags)
    selected_tags_and = _parse_tags(tags_and)
    selected_tags_or = _parse_tags(tags_or)

    items, total = list_articles(
        db,
        search=search,
        source=source,
        journal=journal,
        tags=selected_tags,
        tags_and=selected_tags_and,
        tags_or=selected_tags_or,
        tag_mode=tag_mode,
        check_status=normalized_check_status,
        check_filter=check_filter,
        offset=offset,
        limit=limit,
        sort_by=sort_by,
        sort_order=sort_order,
    )
    return ArticleListResponse(total=total, items=[_to_read(item) for item in items])


@router.get("/export/csv")
def export_articles_csv(
    search: str | None = Query(default=None, description="全文检索关键词"),
    source: str | None = Query(default=None),
    journal: str | None = Query(default=None),
    tags: str | None = Query(default=None, description="逗号分隔，多标签筛选"),
    tags_and: str | None = Query(default=None, description="逗号分隔，AND 标签筛选"),
    tags_or: str | None = Query(default=None, description="逗号分隔，OR 标签筛选"),
    tag_mode: TagMatchMode = Query(default="or"),
    check_status: str | None = Query(default=None),
    check_filter: CheckFilterMode = Query(default="all"),
    sort_by: SortBy = Query(default="ingested_at"),
    sort_order: SortOrder = Query(default="desc"),
    db: Session = Depends(get_db),
) -> Response:
    normalized_check_status = None
    if check_status:
        candidate = check_status.strip().lower()
        if candidate not in {"unchecked", "correct", "error"}:
            raise HTTPException(status_code=400, detail="check_status 必须是 unchecked/correct/error")
        normalized_check_status = candidate

    selected_tags = _parse_tags(tags)
    selected_tags_and = _parse_tags(tags_and)
    selected_tags_or = _parse_tags(tags_or)

    csv_content, rows = build_articles_csv(
        db,
        search=search,
        source=source,
        journal=journal,
        tags=selected_tags,
        tags_and=selected_tags_and,
        tags_or=selected_tags_or,
        tag_mode=tag_mode,
        check_status=normalized_check_status,
        check_filter=check_filter,
        sort_by=sort_by,
        sort_order=sort_order,
    )

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    file_name = f"articles_export_{stamp}.csv"
    headers = {
        "Content-Disposition": f'attachment; filename="{file_name}"',
        "X-Total-Rows": str(rows),
    }
    return Response(content=csv_content.encode("utf-8-sig"), media_type="text/csv; charset=utf-8", headers=headers)


@router.post("/export/jobs/csv", response_model=TaskCreateResponse)
def create_export_csv_job(payload: ExportArticlesCsvPayload) -> TaskCreateResponse:
    task_id = enqueue_task(EXPORT_ARTICLES_CSV_TASK_TYPE, payload.model_dump())
    return TaskCreateResponse(task_id=task_id, status="queued")


@router.post("/fts/rebuild")
def rebuild_fts_endpoint() -> dict[str, str]:
    rebuild_fts_index()
    return {"status": "ok"}


@router.get("/query-filter/dropped", response_model=DroppedQueryFilterDecisionListResponse)
def get_dropped_query_filter_entries(
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=200, ge=1, le=1000),
    db: Session = Depends(get_db),
) -> DroppedQueryFilterDecisionListResponse:
    items, total = list_dropped_query_filter_entries(db, offset=offset, limit=limit)
    return DroppedQueryFilterDecisionListResponse(
        total=total,
        items=[DroppedQueryFilterDecisionRead.model_validate(item) for item in items],
    )


@router.post("/query-filter/dropped/{entry_id}/rescue", response_model=DroppedQueryFilterRescueResponse)
def rescue_dropped_query_filter_entry_endpoint(
    entry_id: int,
    db: Session = Depends(get_db),
) -> DroppedQueryFilterRescueResponse:
    rescued = rescue_dropped_query_filter_entry(db, entry_id=entry_id)
    if rescued is None:
        raise HTTPException(status_code=404, detail="drop 记录不存在")
    db.commit()
    return DroppedQueryFilterRescueResponse(
        status="rescued",
        doi=str(rescued.doi or ""),
        decision_scope_hash=str(rescued.decision_scope_hash or ""),
    )


@router.get("/{article_id}", response_model=ArticleRead)
def get_article(article_id: int, db: Session = Depends(get_db)) -> ArticleRead:
    article = get_article_or_none(db, article_id)
    if article is None:
        raise HTTPException(status_code=404, detail="文献不存在")
    return _to_read(article)


@router.post("", response_model=ArticleRead, status_code=status.HTTP_201_CREATED)
def create_article_endpoint(payload: ArticleCreate, db: Session = Depends(get_db)) -> ArticleRead:
    try:
        article = create_article(db, payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    db.commit()
    db.refresh(article)
    return _to_read(article)


@router.post("/quick", response_model=QuickArticleCreateResponse, status_code=status.HTTP_201_CREATED)
def quick_create_article(payload: QuickArticleCreate, db: Session = Depends(get_db)) -> QuickArticleCreateResponse:
    logs: list[str] = []
    normalized_doi = normalize_doi(payload.doi)
    existing = db.scalar(select(Article).where(Article.doi == normalized_doi))
    if existing is not None:
        # 复用已有条目：标签做并集，避免覆盖原有标签
        existing_tags = _normalize_tag_list([tag.name for tag in existing.tags])
        incoming_tags = _normalize_tag_list(payload.tags)
        merged_tags = _normalize_tag_list([*existing_tags, *incoming_tags])
        merged_note = _merge_note_text(existing.note, payload.note)
        existing_tag_set = set(existing_tags)
        added_tags = [tag for tag in merged_tags if tag not in existing_tag_set]
        note_changed = merged_note != str(existing.note or "").strip()

        _append_local_log(logs, f"命中已存在 DOI，复用 article_id={existing.id}。")

        updated = existing
        if merged_tags != existing_tags or note_changed:
            update_payload = ArticleUpdate(
                tags=merged_tags,
                note=merged_note if note_changed else None,
            )
            updated = update_article(db, existing, update_payload)
            db.commit()
            db.refresh(updated)

        if not incoming_tags:
            _append_local_log(logs, f"标签保持不变（未输入新标签，当前共 {len(existing_tags)} 个）。")
        elif added_tags:
            _append_local_log(logs, f"标签已合并：新增 {len(added_tags)} 个（当前共 {len(merged_tags)} 个）。")
        else:
            _append_local_log(logs, f"标签保持不变（输入标签已全部存在，当前共 {len(existing_tags)} 个）。")
        if note_changed:
            _append_local_log(logs, "备注已补充。")
        elif str(payload.note or "").strip():
            _append_local_log(logs, "备注保持不变（输入内容已存在）。")

        result: dict | None = None
        if payload.run_enrichment:
            try:
                result = enrich_article_by_id(
                    db,
                    updated.id,
                    logger=lambda msg: _append_local_log(logs, msg),
                    include_embedding=payload.include_embedding,
                )
                db.commit()
                db.refresh(updated)
                _append_local_log(logs, "处理完成。")
            except Exception as exc:
                db.rollback()
                db.refresh(updated)
                _append_local_log(logs, f"补全执行失败: {exc}")
                result = {"article_id": updated.id, "skipped": True, "error": str(exc), "filled_fields": []}
        else:
            _append_local_log(logs, "仅录入模式：已跳过自动补全。")
            result = {
                "article_id": updated.id,
                "doi": updated.doi,
                "insert_only": True,
                "skipped": True,
                "filled_fields": [],
                "metadata_filled": [],
                "ai_filled": [],
                "embedding_generated": False,
            }
        return QuickArticleCreateResponse(
            article=_to_read(updated),
            enrichment_job_id=None,
            logs=logs,
            enrichment_result=result,
        )

    create_payload = ArticleCreate(doi=payload.doi, tags=payload.tags, note=payload.note)
    try:
        article = create_article(db, create_payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    db.commit()
    db.refresh(article)
    _append_local_log(logs, f"新文献已录入，article_id={article.id}。")

    if payload.run_enrichment:
        try:
            result = enrich_article_by_id(
                db,
                article.id,
                logger=lambda msg: _append_local_log(logs, msg),
                include_embedding=payload.include_embedding,
            )
            db.commit()
            db.refresh(article)
            _append_local_log(logs, "处理完成。")
        except Exception as exc:
            db.rollback()
            db.refresh(article)
            _append_local_log(logs, f"补全执行失败: {exc}")
            result = {"article_id": article.id, "skipped": True, "error": str(exc), "filled_fields": []}
    else:
        _append_local_log(logs, "仅录入模式：已跳过自动补全。")
        result = {
            "article_id": article.id,
            "doi": article.doi,
            "insert_only": True,
            "skipped": True,
            "filled_fields": [],
            "metadata_filled": [],
            "ai_filled": [],
            "embedding_generated": False,
        }
    return QuickArticleCreateResponse(
        article=_to_read(article),
        enrichment_job_id=None,
        logs=logs,
        enrichment_result=result,
    )


@router.put("/{article_id}", response_model=ArticleRead)
def update_article_endpoint(article_id: int, payload: ArticleUpdate, db: Session = Depends(get_db)) -> ArticleRead:
    article = get_article_or_none(db, article_id)
    if article is None:
        raise HTTPException(status_code=404, detail="文献不存在")

    article = update_article(db, article, payload)
    db.commit()
    db.refresh(article)
    return _to_read(article)


@router.put("/{article_id}/tags", response_model=ArticleRead)
def update_article_tags(article_id: int, payload: ArticleTagUpdate, db: Session = Depends(get_db)) -> ArticleRead:
    article = get_article_or_none(db, article_id)
    if article is None:
        raise HTTPException(status_code=404, detail="文献不存在")

    article = update_article(db, article, ArticleUpdate(tags=payload.tags))
    db.commit()
    db.refresh(article)
    return _to_read(article)


@router.delete("/{article_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_article_endpoint(article_id: int, db: Session = Depends(get_db)) -> None:
    article = get_article_or_none(db, article_id)
    if article is None:
        raise HTTPException(status_code=404, detail="文献不存在")

    delete_article(db, article)
    db.commit()
