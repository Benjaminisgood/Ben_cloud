from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from benself_api.core.config import get_settings
from benself_api.db.session import get_db
from benself_api.repositories.graph_sync_runs_repo import create_graph_sync_run
from benself_api.schemas.graph import GraphSyncRunCreate
from benself_api.services.graphiti_sync import GraphitiUnavailableError, run_graph_sync, search_graphiti

from ..deps import get_session_user
from ..templating import render_template

router = APIRouter(tags=["pages"])


@router.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    user = get_session_user(request)
    if not user:
        return RedirectResponse("/login", status_code=303)

    settings = get_settings()
    graph_query = str(request.query_params.get("q", "")).strip()
    graph_results = None
    graph_error = None
    if graph_query:
        try:
            graph_results = await search_graphiti(settings=settings, query=graph_query, limit=6)
        except GraphitiUnavailableError as exc:
            graph_error = str(exc)

    return render_template(
        request,
        "dashboard.html",
        {
            "title": "Benself | Memory Search",
            "graph_query": graph_query,
            "graph_results": graph_results.model_dump() if graph_results else None,
            "graph_error": graph_error,
            "theme": {
                "primary": "#123b42",
                "secondary": "#ff9f6e",
                "canvas": "#f3ecdf",
                "ink": "#172229",
            },
        },
    )


@router.get("/portal")
def portal() -> RedirectResponse:
    return RedirectResponse("/", status_code=303)


@router.post("/graph-sync-runs")
async def submit_graph_sync(request: Request, db: Session = Depends(get_db)):
    user = get_session_user(request)
    if not user:
        return RedirectResponse("/login", status_code=303)

    form = await request.form()
    payload = GraphSyncRunCreate(mode=str(form.get("mode", "preview")).strip() or "preview")
    outcome = await run_graph_sync(settings=get_settings(), mode=payload.mode)
    create_graph_sync_run(
        db,
        mode=payload.mode,
        status=outcome.status,
        raw_episode_count=outcome.raw_episode_count,
        confirmed_episode_count=outcome.confirmed_episode_count,
        backend=outcome.backend,
        message=outcome.message,
        created_by=user["username"],
    )
    return RedirectResponse("/", status_code=303)
