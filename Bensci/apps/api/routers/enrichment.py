from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from apps.api.deps import get_db
from apps.db.models import Article
from apps.models.schemas import (
    EnrichmentJobControlResponse,
    AutoEnrichmentToggleRequest,
    AutoEnrichmentToggleResponse,
    AutoEnrichmentStatusResponse,
    EnrichmentFillRequest,
    EnrichmentJobCreateResponse,
    EnrichmentJobStatusResponse,
)
from apps.services.auto_enrichment_scheduler import get_auto_enrichment_enabled, set_auto_enrichment_enabled
from apps.services.enrichment_jobs import (
    cancel_enrichment_job,
    create_fill_empty_enrichment_job,
    create_single_article_enrichment_job,
    get_latest_auto_fill_job_snapshot,
    get_enrichment_job_snapshot,
    pause_enrichment_job,
    resume_enrichment_job,
)

router = APIRouter(prefix="/enrichment", tags=["enrichment"])


@router.post("/jobs/fill-empty", response_model=EnrichmentJobCreateResponse)
def create_fill_empty_job(payload: EnrichmentFillRequest) -> EnrichmentJobCreateResponse:
    job_id = create_fill_empty_enrichment_job(payload)
    return EnrichmentJobCreateResponse(job_id=job_id, status="queued")


@router.post("/jobs/article/{article_id}", response_model=EnrichmentJobCreateResponse)
def create_single_article_job(
    article_id: int,
    include_embedding: bool = Query(default=False),
    db: Session = Depends(get_db),
) -> EnrichmentJobCreateResponse:
    exists = db.get(Article, article_id)
    if exists is None:
        raise HTTPException(status_code=404, detail="文献不存在")

    job_id = create_single_article_enrichment_job(article_id, include_embedding=include_embedding)
    return EnrichmentJobCreateResponse(job_id=job_id, status="queued")


@router.get("/jobs/{job_id}", response_model=EnrichmentJobStatusResponse)
def get_job_status(
    job_id: str,
    from_line: int = Query(default=0, ge=0),
) -> EnrichmentJobStatusResponse:
    snapshot = get_enrichment_job_snapshot(job_id, from_line=from_line)
    if snapshot is None:
        raise HTTPException(status_code=404, detail="任务不存在")
    return EnrichmentJobStatusResponse.model_validate(snapshot)


@router.post("/jobs/{job_id}/pause", response_model=EnrichmentJobControlResponse)
def pause_job(job_id: str) -> EnrichmentJobControlResponse:
    snapshot = pause_enrichment_job(job_id)
    if snapshot is None:
        raise HTTPException(status_code=404, detail="任务不存在")
    return EnrichmentJobControlResponse(
        job_id=job_id,
        status=str(snapshot.get("status") or "paused"),
        message="补全任务已暂停。",
    )


@router.post("/jobs/{job_id}/resume", response_model=EnrichmentJobControlResponse)
def resume_job(job_id: str) -> EnrichmentJobControlResponse:
    snapshot = resume_enrichment_job(job_id)
    if snapshot is None:
        raise HTTPException(status_code=404, detail="任务不存在")
    return EnrichmentJobControlResponse(
        job_id=job_id,
        status=str(snapshot.get("status") or "running"),
        message="补全任务已继续。",
    )


@router.post("/jobs/{job_id}/cancel", response_model=EnrichmentJobControlResponse)
def cancel_job(job_id: str) -> EnrichmentJobControlResponse:
    snapshot = cancel_enrichment_job(job_id)
    if snapshot is None:
        raise HTTPException(status_code=404, detail="任务不存在")
    return EnrichmentJobControlResponse(
        job_id=job_id,
        status=str(snapshot.get("status") or "cancel_requested"),
        message="补全任务已收到停止请求。",
    )


@router.get("/auto/status", response_model=AutoEnrichmentStatusResponse)
def get_auto_fill_status(
    from_line: int = Query(default=0, ge=0),
) -> AutoEnrichmentStatusResponse:
    auto_enabled = get_auto_enrichment_enabled()
    snapshot = get_latest_auto_fill_job_snapshot(from_line=from_line)
    if snapshot is None:
        return AutoEnrichmentStatusResponse(auto_enabled=auto_enabled, has_job=False, status="idle")
    payload = {"auto_enabled": auto_enabled, "has_job": True, **snapshot}
    return AutoEnrichmentStatusResponse.model_validate(payload)


@router.post("/auto/enabled", response_model=AutoEnrichmentToggleResponse)
def update_auto_fill_enabled(payload: AutoEnrichmentToggleRequest) -> AutoEnrichmentToggleResponse:
    enabled = set_auto_enrichment_enabled(payload.enabled)
    message = "后台自动补全已开启。" if enabled else "后台自动补全已关闭。"
    return AutoEnrichmentToggleResponse(enabled=enabled, message=message)
