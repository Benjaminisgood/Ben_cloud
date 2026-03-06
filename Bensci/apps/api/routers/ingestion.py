from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from apps.api.deps import get_db
from apps.models.schemas import (
    IngestJobControlResponse,
    IngestJobCreateResponse,
    IngestJobProvidersUpdateRequest,
    IngestJobStatusResponse,
    IngestRequest,
    IngestResponse,
)
from apps.services.ingestion_service import ingest_metadata
from apps.services.ingestion_jobs import (
    cancel_ingestion_job,
    create_ingestion_job,
    get_ingestion_job_snapshot,
    pause_ingestion_job,
    resume_ingestion_job,
    update_ingestion_job_providers,
)

router = APIRouter(prefix="/ingestion", tags=["ingestion"])


@router.post("/fetch", response_model=IngestResponse)
def fetch_and_ingest(payload: IngestRequest, db: Session = Depends(get_db)) -> IngestResponse:
    return ingest_metadata(
        db,
        query=payload.query,
        providers=payload.providers,
        max_results=payload.max_results,
        save_tags=payload.save_tags,
        query_filter_mode=payload.query_filter_mode,
        query_similarity_threshold=payload.query_similarity_threshold,
        llm_scoring_prompt=payload.llm_scoring_prompt,
        llm_review_existing_articles=payload.llm_review_existing_articles,
        llm_review_dropped_articles=payload.llm_review_dropped_articles,
        published_from=payload.published_from,
        published_to=payload.published_to,
        required_keywords=payload.required_keywords,
        optional_keywords=payload.optional_keywords,
        excluded_keywords=payload.excluded_keywords,
        journal_whitelist=payload.journal_whitelist,
        journal_blacklist=payload.journal_blacklist,
        min_citation_count=payload.min_citation_count,
        min_impact_factor=payload.min_impact_factor,
    )


@router.post("/jobs", response_model=IngestJobCreateResponse)
def create_ingestion_job_endpoint(payload: IngestRequest) -> IngestJobCreateResponse:
    job_id = create_ingestion_job(payload)
    return IngestJobCreateResponse(job_id=job_id, status="queued")


@router.get("/jobs/{job_id}", response_model=IngestJobStatusResponse)
def get_ingestion_job_endpoint(
    job_id: str,
    from_line: int = Query(default=0, ge=0),
) -> IngestJobStatusResponse:
    snapshot = get_ingestion_job_snapshot(job_id=job_id, from_line=from_line)
    if snapshot is None:
        raise HTTPException(status_code=404, detail="任务不存在")
    return IngestJobStatusResponse.model_validate(snapshot)


def _extract_snapshot_providers(snapshot: dict) -> list[str]:
    payload = snapshot.get("payload") if isinstance(snapshot, dict) else {}
    providers = payload.get("providers") if isinstance(payload, dict) else []
    if not isinstance(providers, list):
        return []
    output: list[str] = []
    seen: set[str] = set()
    for item in providers:
        value = str(item or "").strip().lower()
        if not value or value in seen:
            continue
        seen.add(value)
        output.append(value)
    return output


@router.post("/jobs/{job_id}/pause", response_model=IngestJobControlResponse)
def pause_ingestion_job_endpoint(job_id: str) -> IngestJobControlResponse:
    snapshot = pause_ingestion_job(job_id)
    if snapshot is None:
        raise HTTPException(status_code=404, detail="任务不存在")
    return IngestJobControlResponse(
        job_id=job_id,
        status=str(snapshot.get("status") or ""),
        message="任务已标记为暂停状态。",
        providers=_extract_snapshot_providers(snapshot),
    )


@router.post("/jobs/{job_id}/resume", response_model=IngestJobControlResponse)
def resume_ingestion_job_endpoint(job_id: str) -> IngestJobControlResponse:
    snapshot = resume_ingestion_job(job_id)
    if snapshot is None:
        raise HTTPException(status_code=404, detail="任务不存在")
    return IngestJobControlResponse(
        job_id=job_id,
        status=str(snapshot.get("status") or ""),
        message="任务继续执行。",
        providers=_extract_snapshot_providers(snapshot),
    )


@router.post("/jobs/{job_id}/cancel", response_model=IngestJobControlResponse)
def cancel_ingestion_job_endpoint(job_id: str) -> IngestJobControlResponse:
    snapshot = cancel_ingestion_job(job_id)
    if snapshot is None:
        raise HTTPException(status_code=404, detail="任务不存在")
    return IngestJobControlResponse(
        job_id=job_id,
        status=str(snapshot.get("status") or ""),
        message="任务已收到停止请求。",
        providers=_extract_snapshot_providers(snapshot),
    )


@router.patch("/jobs/{job_id}/providers", response_model=IngestJobControlResponse)
def update_ingestion_job_providers_endpoint(
    job_id: str,
    payload: IngestJobProvidersUpdateRequest,
) -> IngestJobControlResponse:
    try:
        snapshot = update_ingestion_job_providers(job_id, payload.providers)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    if snapshot is None:
        raise HTTPException(status_code=404, detail="任务不存在")
    return IngestJobControlResponse(
        job_id=job_id,
        status=str(snapshot.get("status") or ""),
        message="已更新任务 provider 列表。",
        providers=_extract_snapshot_providers(snapshot),
    )
