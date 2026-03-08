
from __future__ import annotations

from fastapi import APIRouter, Depends

from benself_api.api.deps import require_user
from benself_api.core.config import get_settings
from benself_api.schemas.dashboard import AgentContextPreview, ConfirmedFactDomain, DashboardSnapshot, RawJournalFact
from benself_api.services.self_context import build_dashboard_snapshot

router = APIRouter(tags=["dashboard"])


@router.get("/dashboard", response_model=DashboardSnapshot)
def dashboard(_: dict[str, str] = Depends(require_user)) -> DashboardSnapshot:
    return build_dashboard_snapshot(get_settings())


@router.get("/raw-journals", response_model=list[RawJournalFact])
def raw_journals(_: dict[str, str] = Depends(require_user)) -> list[RawJournalFact]:
    return build_dashboard_snapshot(get_settings()).raw_journals


@router.get("/confirmed-facts", response_model=list[ConfirmedFactDomain])
def confirmed_facts(_: dict[str, str] = Depends(require_user)) -> list[ConfirmedFactDomain]:
    return build_dashboard_snapshot(get_settings()).confirmed_domains


@router.get("/agent-context", response_model=AgentContextPreview)
def agent_context(_: dict[str, str] = Depends(require_user)) -> AgentContextPreview:
    return build_dashboard_snapshot(get_settings()).agent_context
