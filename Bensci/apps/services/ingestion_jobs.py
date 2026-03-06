from __future__ import annotations

from collections.abc import Callable
from typing import Any

from apps.core.config import settings
from apps.db.session import SessionLocal
from apps.models.schemas import IngestRequest
from apps.services.ingestion_service import ingest_metadata
from apps.services.task_queue import (
    append_task_log,
    cancel_task,
    enqueue_task,
    get_current_task_id,
    get_task_snapshot,
    is_task_cancel_requested,
    pause_task,
    register_task_handler,
    replace_task_payload,
    resume_task,
    wait_if_task_paused,
)

INGESTION_TASK_TYPE = "ingestion.fetch"


def _normalized_providers(raw: list[str] | None) -> list[str]:
    if not raw:
        return []
    seen: set[str] = set()
    providers: list[str] = []
    for item in raw:
        value = str(item or "").strip().lower()
        if not value or value in seen:
            continue
        seen.add(value)
        providers.append(value)
    return providers


def _is_ingestion_snapshot(snapshot: dict[str, Any] | None) -> bool:
    return bool(snapshot) and str(snapshot.get("task_type") or "").strip() == INGESTION_TASK_TYPE


def _live_provider_list(task_id: str, fallback: list[str] | None) -> list[str]:
    snapshot = get_task_snapshot(task_id=task_id, from_line=0)
    payload = snapshot.get("payload") if isinstance(snapshot, dict) else {}
    providers = payload.get("providers") if isinstance(payload, dict) else None
    normalized = _normalized_providers(providers if isinstance(providers, list) else fallback)
    return list(normalized)


def _run_ingestion_task(payload: dict[str, Any], logger: Callable[[str], None]) -> dict[str, Any]:
    request = IngestRequest.model_validate(payload)
    current_task_id = get_current_task_id()
    provider_fallback = request.providers or list(settings.default_providers)
    session = SessionLocal()
    try:
        result = ingest_metadata(
            session,
            query=request.query,
            providers=request.providers,
            max_results=request.max_results,
            save_tags=request.save_tags,
            query_filter_mode=request.query_filter_mode,
            query_similarity_threshold=request.query_similarity_threshold,
            llm_scoring_prompt=request.llm_scoring_prompt,
            llm_review_existing_articles=request.llm_review_existing_articles,
            llm_review_dropped_articles=request.llm_review_dropped_articles,
            published_from=request.published_from,
            published_to=request.published_to,
            required_keywords=request.required_keywords,
            optional_keywords=request.optional_keywords,
            excluded_keywords=request.excluded_keywords,
            journal_whitelist=request.journal_whitelist,
            journal_blacklist=request.journal_blacklist,
            min_citation_count=request.min_citation_count,
            min_impact_factor=request.min_impact_factor,
            cancel_check=(lambda: is_task_cancel_requested(current_task_id)) if current_task_id else None,
            pause_wait_callback=(
                lambda: wait_if_task_paused(current_task_id, logger=logger)
            )
            if current_task_id
            else None,
            provider_keys_provider=(
                lambda: _live_provider_list(current_task_id, provider_fallback)
            )
            if current_task_id
            else None,
            log_callback=logger,
        )
        # ingest_metadata() 内部已提交事务，二次提交是安全的。
        session.commit()
        return result.model_dump()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def create_ingestion_job(payload: IngestRequest) -> str:
    return enqueue_task(INGESTION_TASK_TYPE, payload.model_dump())


def get_ingestion_job_snapshot(job_id: str, from_line: int = 0) -> dict | None:
    snapshot = get_task_snapshot(task_id=job_id, from_line=from_line)
    if snapshot is None:
        return None
    return {
        "job_id": snapshot["job_id"],
        "task_type": snapshot["task_type"],
        "status": snapshot["status"],
        "payload": snapshot["payload"],
        "logs": snapshot["logs"],
        "next_line": snapshot["next_line"],
        "result": snapshot["result"] or None,
        "error": snapshot["error"],
        "created_at": snapshot["created_at"],
        "started_at": snapshot["started_at"],
        "finished_at": snapshot["finished_at"],
    }


def pause_ingestion_job(job_id: str) -> dict | None:
    snapshot = get_task_snapshot(task_id=job_id, from_line=0)
    if not _is_ingestion_snapshot(snapshot):
        return None
    updated = pause_task(job_id)
    if updated is not None:
        append_task_log(job_id, "收到暂停请求。")
    return updated


def resume_ingestion_job(job_id: str) -> dict | None:
    snapshot = get_task_snapshot(task_id=job_id, from_line=0)
    if not _is_ingestion_snapshot(snapshot):
        return None
    updated = resume_task(job_id)
    if updated is not None:
        append_task_log(job_id, "收到继续请求。")
    return updated


def cancel_ingestion_job(job_id: str) -> dict | None:
    snapshot = get_task_snapshot(task_id=job_id, from_line=0)
    if not _is_ingestion_snapshot(snapshot):
        return None
    updated = cancel_task(job_id)
    if updated is not None:
        append_task_log(job_id, "收到停止请求。")
    return updated


def update_ingestion_job_providers(job_id: str, providers: list[str]) -> dict | None:
    snapshot = get_task_snapshot(task_id=job_id, from_line=0)
    if not _is_ingestion_snapshot(snapshot):
        return None
    status = str(snapshot.get("status") or "")
    if status in {"completed", "failed", "cancelled"}:
        raise RuntimeError("任务已结束，不能再调整 provider。")

    normalized = _normalized_providers(providers)
    if not normalized:
        raise ValueError("providers 不能为空。")

    payload = dict(snapshot.get("payload") or {})
    payload["providers"] = normalized
    updated = replace_task_payload(job_id, payload)
    if updated is not None:
        append_task_log(job_id, f"运行参数更新: providers={normalized}")
    return updated


register_task_handler(INGESTION_TASK_TYPE, _run_ingestion_task)
