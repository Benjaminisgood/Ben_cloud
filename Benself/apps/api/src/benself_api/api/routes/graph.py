from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from benself_api.api.deps import require_user
from benself_api.core.config import get_settings
from benself_api.db.session import get_db
from benself_api.repositories.graph_sync_runs_repo import create_graph_sync_run, list_graph_sync_runs
from benself_api.schemas.graph import GraphSearchResponse, GraphSyncRunCreate, GraphSyncRunRead
from benself_api.services.graphiti_sync import GraphitiUnavailableError, run_graph_sync, search_graphiti

router = APIRouter(tags=["graphiti"])


@router.get("/graph-sync-runs", response_model=list[GraphSyncRunRead])
def get_graph_sync_runs(
    _: dict[str, str] = Depends(require_user),
    db: Session = Depends(get_db),
) -> list[GraphSyncRunRead]:
    return list_graph_sync_runs(db)


@router.post("/graph-sync-runs", response_model=GraphSyncRunRead, status_code=status.HTTP_201_CREATED)
async def post_graph_sync_run(
    payload: GraphSyncRunCreate,
    user: dict[str, str] = Depends(require_user),
    db: Session = Depends(get_db),
) -> GraphSyncRunRead:
    outcome = await run_graph_sync(settings=get_settings(), mode=payload.mode)
    return create_graph_sync_run(
        db,
        mode=payload.mode,
        status=outcome.status,
        raw_episode_count=outcome.raw_episode_count,
        confirmed_episode_count=outcome.confirmed_episode_count,
        backend=outcome.backend,
        message=outcome.message,
        created_by=user["username"],
    )


@router.get("/graph-search", response_model=GraphSearchResponse)
async def get_graph_search(
    q: str = Query(..., min_length=2, max_length=120),
    limit: int = Query(default=6, ge=1, le=10),
    _: dict[str, str] = Depends(require_user),
) -> GraphSearchResponse:
    try:
        return await search_graphiti(settings=get_settings(), query=q, limit=limit)
    except GraphitiUnavailableError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
