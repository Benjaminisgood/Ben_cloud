from __future__ import annotations

from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any

from sqlalchemy import or_, select

from apps.db.models import Article, Task
from apps.db.session import SessionLocal
from apps.models.schemas import EnrichmentFillRequest
from apps.services.ai_enrichment import enrich_article_by_id
from apps.services.task_queue import (
    append_task_log,
    cancel_task,
    enqueue_task,
    get_current_task_id,
    get_task_snapshot,
    is_task_cancel_requested,
    pause_task,
    register_task_handler,
    resume_task,
    wait_if_task_paused,
)

ENRICHMENT_TASK_TYPE_SINGLE = "enrichment.article"
ENRICHMENT_TASK_TYPE_FILL_EMPTY = "enrichment.fill_empty"
ENRICHMENT_TASK_TYPE_FILL_EMPTY_AUTO = "enrichment.fill_empty.auto"


def _missing_predicate():
    return or_(
        Article.title.is_(None),
        Article.title == "",
        Article.keywords.is_(None),
        Article.keywords == "",
        Article.abstract.is_(None),
        Article.abstract == "",
        Article.journal.is_(None),
        Article.journal == "",
        Article.corresponding_author.is_(None),
        Article.corresponding_author == "",
        Article.affiliations.is_(None),
        Article.affiliations == "",
        Article.source.is_(None),
        Article.source == "",
        Article.publisher.is_(None),
        Article.publisher == "",
        Article.published_date.is_(None),
        Article.published_date == "",
        Article.url.is_(None),
        Article.url == "",
    )


def _get_target_article_ids(limit: int) -> list[int]:
    session = SessionLocal()
    try:
        stmt = (
            select(Article.id)
            .where(Article.check_status != "correct")
            .where(_missing_predicate())
            .order_by(Article.ingested_at.desc(), Article.id.desc())
            .limit(limit)
        )
        return list(session.scalars(stmt))
    finally:
        session.close()


def _enrich_one_article(article_id: int, logger: Callable[[str], None]) -> dict[str, Any]:
    session = SessionLocal()
    try:
        result = enrich_article_by_id(
            session,
            article_id,
            logger=logger,
        )
        session.commit()
        return result
    except Exception as exc:  # pragma: no cover
        session.rollback()
        logger(f"[id={article_id}] 补全失败: {exc}")
        return {
            "article_id": article_id,
            "skipped": True,
            "reason": "exception",
            "error": str(exc),
            "filled_fields": [],
            "metadata_filled": [],
            "ai_filled": [],
        }
    finally:
        session.close()


def _run_single_article_task(payload: dict[str, Any], logger: Callable[[str], None]) -> dict[str, Any]:
    article_id = int(payload.get("article_id") or 0)
    include_embedding = bool(payload.get("include_embedding", False))
    if article_id <= 0:
        raise ValueError("article_id 必须是正整数")

    logger(f"开始单篇补全，article_id={article_id}, include_embedding={include_embedding}")
    session = SessionLocal()
    try:
        result = enrich_article_by_id(
            session,
            article_id,
            logger=logger,
            include_embedding=include_embedding,
        )
        session.commit()
    except Exception as exc:  # pragma: no cover
        session.rollback()
        logger(f"[id={article_id}] 补全失败: {exc}")
        raise
    finally:
        session.close()
    logger("单篇补全任务完成。")

    return {
        "kind": "single",
        "article_id": article_id,
        "include_embedding": include_embedding,
        "filled_fields": result.get("filled_fields", []),
        "embedding_generated": bool(result.get("embedding_generated", False)),
        "skipped": result.get("skipped", False),
        "reason": result.get("reason"),
        "error": result.get("error"),
    }


def _run_fill_empty_task(payload: dict[str, Any], logger: Callable[[str], None]) -> dict[str, Any]:
    request = EnrichmentFillRequest.model_validate(payload)

    ids = _get_target_article_ids(limit=request.limit)
    logger(f"待补全文献数: {len(ids)}")

    if not ids:
        logger("没有可补全文献。")
        return {
            "kind": "fill_empty",
            "processed": 0,
            "updated": 0,
            "skipped": 0,
            "filled_fields": 0,
        }

    updated = 0
    skipped = 0
    processed = 0
    filled_fields_total = 0
    cancelled = False

    max_workers = max(1, min(request.workers, len(ids)))
    logger(f"启用线程数: {max_workers}")
    current_task_id = get_current_task_id()

    with ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="enrich") as pool:
        for start in range(0, len(ids), max_workers):
            if current_task_id:
                cancelled = wait_if_task_paused(current_task_id, logger=logger)
                if cancelled or is_task_cancel_requested(current_task_id):
                    cancelled = True
                    logger("收到停止请求，批量补全提前结束。")
                    break

            batch_ids = ids[start : start + max_workers]
            future_map = {pool.submit(_enrich_one_article, article_id, logger): article_id for article_id in batch_ids}
            for future in as_completed(future_map):
                result = future.result()
                processed += 1
                fields = result.get("filled_fields") or []
                if fields:
                    updated += 1
                    filled_fields_total += len(fields)
                else:
                    skipped += 1

            if current_task_id and is_task_cancel_requested(current_task_id):
                cancelled = True
                logger("收到停止请求，当前批次已完成，任务结束。")
                break

    if cancelled:
        logger("批量补全任务已按请求停止。")
    else:
        logger("批量补全任务完成。")
    return {
        "kind": "fill_empty",
        "processed": processed,
        "updated": updated,
        "skipped": skipped,
        "filled_fields": filled_fields_total,
        "cancelled": cancelled,
    }


def create_single_article_enrichment_job(article_id: int, *, include_embedding: bool = False) -> str:
    return enqueue_task(
        ENRICHMENT_TASK_TYPE_SINGLE,
        {"article_id": article_id, "include_embedding": include_embedding},
    )


def create_fill_empty_enrichment_job(payload: EnrichmentFillRequest) -> str:
    return enqueue_task(ENRICHMENT_TASK_TYPE_FILL_EMPTY, payload.model_dump())


def create_auto_fill_empty_enrichment_job(payload: EnrichmentFillRequest) -> str:
    return enqueue_task(ENRICHMENT_TASK_TYPE_FILL_EMPTY_AUTO, payload.model_dump())


def get_enrichment_job_snapshot(job_id: str, from_line: int = 0) -> dict | None:
    snapshot = get_task_snapshot(task_id=job_id, from_line=from_line)
    if snapshot is None:
        return None
    return {
        "job_id": snapshot["job_id"],
        "status": snapshot["status"],
        "logs": snapshot["logs"],
        "next_line": snapshot["next_line"],
        "result": snapshot["result"] or None,
        "error": snapshot["error"],
        "created_at": snapshot["created_at"],
        "started_at": snapshot["started_at"],
        "finished_at": snapshot["finished_at"],
    }


def get_latest_auto_fill_job_snapshot(from_line: int = 0) -> dict | None:
    session = SessionLocal()
    try:
        latest_id = session.scalar(
            select(Task.id)
            .where(Task.task_type == ENRICHMENT_TASK_TYPE_FILL_EMPTY_AUTO)
            .order_by(Task.created_at.desc(), Task.id.desc())
            .limit(1)
        )
    finally:
        session.close()

    if not latest_id:
        return None
    return get_enrichment_job_snapshot(str(latest_id), from_line=from_line)


def _list_active_auto_fill_job_ids() -> list[str]:
    session = SessionLocal()
    try:
        rows = session.scalars(
            select(Task.id)
            .where(Task.task_type == ENRICHMENT_TASK_TYPE_FILL_EMPTY_AUTO)
            .where(Task.status.in_(["queued", "running", "paused", "cancel_requested"]))
            .order_by(Task.created_at.desc(), Task.id.desc())
        ).all()
        return [str(item) for item in rows]
    finally:
        session.close()


def cancel_active_auto_fill_jobs() -> list[str]:
    cancelled: list[str] = []
    for task_id in _list_active_auto_fill_job_ids():
        snapshot = cancel_task(task_id)
        if snapshot is not None:
            append_task_log(task_id, "收到停止请求（自动补全开关关闭）。")
            cancelled.append(task_id)
    return cancelled


def has_pending_auto_fill_job() -> bool:
    session = SessionLocal()
    try:
        task_id = session.scalar(
            select(Task.id)
            .where(Task.task_type == ENRICHMENT_TASK_TYPE_FILL_EMPTY_AUTO)
            .where(Task.status.in_(["queued", "running", "paused", "cancel_requested"]))
            .limit(1)
        )
        return bool(task_id)
    finally:
        session.close()


def pause_enrichment_job(job_id: str) -> dict | None:
    snapshot = get_task_snapshot(task_id=job_id, from_line=0)
    if snapshot is None:
        return None
    updated = pause_task(job_id)
    if updated is not None:
        append_task_log(job_id, "收到暂停请求。")
    return updated


def resume_enrichment_job(job_id: str) -> dict | None:
    snapshot = get_task_snapshot(task_id=job_id, from_line=0)
    if snapshot is None:
        return None
    updated = resume_task(job_id)
    if updated is not None:
        append_task_log(job_id, "收到继续请求。")
    return updated


def cancel_enrichment_job(job_id: str) -> dict | None:
    snapshot = get_task_snapshot(task_id=job_id, from_line=0)
    if snapshot is None:
        return None
    updated = cancel_task(job_id)
    if updated is not None:
        append_task_log(job_id, "收到停止请求。")
    return updated


register_task_handler(ENRICHMENT_TASK_TYPE_SINGLE, _run_single_article_task)
register_task_handler(ENRICHMENT_TASK_TYPE_FILL_EMPTY, _run_fill_empty_task)
register_task_handler(ENRICHMENT_TASK_TYPE_FILL_EMPTY_AUTO, _run_fill_empty_task)
