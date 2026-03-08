from __future__ import annotations

from typing import Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ...db.session import get_db
from ...schemas.projects import (
    ProjectControlResponse,
    ProjectEnvFileResponse,
    ProjectEnvUpdatePayload,
    ProjectEnvUpdateResponse,
    ProjectLogsResponse,
    ProjectsStatusResponse,
)
from ...services.health import run_health_checks
from ...services.metrics import inc_counter
from ...services.project_control import run_project_control_action
from ...services.project_env import read_project_env_file, update_project_env_file
from ...services.project_views import (
    assemble_project_logs_response,
    assemble_projects_status_response,
    ensure_known_project_id,
)
from ...web.deps import require_admin_session_user_or_403, require_session_user_or_401

router = APIRouter(tags=["projects"])


class ProjectControlPayload(BaseModel):
    action: Literal["start", "stop", "restart", "status"]


@router.get("/projects/status", response_model=ProjectsStatusResponse)
async def projects_status(request: Request, db: Session = Depends(get_db)):
    """Return health + click stats for all projects (for live dashboard updates)."""
    user = require_session_user_or_401(request, db)
    return assemble_projects_status_response(db=db, current_user=user)


@router.post("/projects/check-health")
async def trigger_health_check(request: Request, db: Session = Depends(get_db)):
    """Manually trigger a health check round."""
    require_admin_session_user_or_403(request, db)

    await run_health_checks()
    return {"ok": True}


@router.post("/projects/{project_id}/control", response_model=ProjectControlResponse)
async def control_project(
    project_id: str,
    payload: ProjectControlPayload,
    request: Request,
    db: Session = Depends(get_db),
):
    user = require_admin_session_user_or_403(request, db)

    try:
        normalized_project_id = ensure_known_project_id(project_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="project_not_found") from exc

    try:
        result = run_project_control_action(
            normalized_project_id,
            payload.action,
            db=db,
            operator=user.username,
        )
    except RuntimeError as exc:
        inc_counter("benbot_project_control_failure_total")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc

    if payload.action in {"start", "stop", "restart"}:
        await run_health_checks()
    if not result.ok:
        inc_counter("benbot_project_control_failure_total")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=result.output or "control_command_failed",
        )

    if payload.action in {"start", "stop", "restart"}:
        inc_counter("benbot_project_control_success_total")

    return {
        "ok": True,
        "project_id": result.project_id,
        "action": result.action,
        "service_state": result.service_state,
        "output": result.output,
    }


@router.get("/projects/{project_id}/logs", response_model=ProjectLogsResponse)
async def get_project_logs(
    project_id: str,
    request: Request,
    db: Session = Depends(get_db),
    level: Optional[str] = Query(default=None, description="按日志级别过滤: INFO / WARNING / ERROR"),
    limit: int = Query(default=100, ge=1, le=200, description="每页条数"),
    offset: int = Query(default=0, ge=0, description="分页偏移"),
):
    """
    管理员专属：查询指定项目的运行日志与报错记录。

    - level: 可选，过滤级别 INFO / WARNING / ERROR
    - limit: 每次最多返回 200 条
    - offset: 分页偏移
    """
    require_admin_session_user_or_403(request, db)
    try:
        return assemble_project_logs_response(
            db=db,
            project_id=project_id,
            level=level,
            limit=limit,
            offset=offset,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.get("/projects/{project_id}/env", response_model=ProjectEnvFileResponse)
def get_project_env_file(
    project_id: str,
    request: Request,
    db: Session = Depends(get_db),
):
    require_admin_session_user_or_403(request, db)
    try:
        snapshot = read_project_env_file(project_id)
    except ValueError as exc:
        detail = str(exc)
        status_code = status.HTTP_404_NOT_FOUND if detail in {"project_not_found", "project_root_not_found"} else status.HTTP_400_BAD_REQUEST
        raise HTTPException(status_code=status_code, detail=detail) from exc

    return ProjectEnvFileResponse(
        project_id=snapshot.project_id,
        project_name=snapshot.project_name,
        path=snapshot.path,
        loaded_from=snapshot.loaded_from,
        exists=snapshot.exists,
        source=snapshot.source,
        updated_at=snapshot.updated_at.isoformat() if snapshot.updated_at else None,
        content=snapshot.content,
    )


@router.put("/projects/{project_id}/env", response_model=ProjectEnvUpdateResponse)
def put_project_env_file(
    project_id: str,
    payload: ProjectEnvUpdatePayload,
    request: Request,
    db: Session = Depends(get_db),
):
    operator = require_admin_session_user_or_403(request, db)
    try:
        result = update_project_env_file(
            project_id=project_id,
            content=payload.content,
            db=db,
            operator=operator.username,
        )
    except ValueError as exc:
        detail = str(exc)
        status_code = status.HTTP_404_NOT_FOUND if detail in {"project_not_found", "project_root_not_found"} else status.HTTP_400_BAD_REQUEST
        raise HTTPException(status_code=status_code, detail=detail) from exc

    return ProjectEnvUpdateResponse(
        ok=True,
        project_id=result.project_id,
        project_name=result.project_name,
        path=result.path,
        loaded_from=result.loaded_from,
        exists=result.exists,
        source=result.source,
        updated_at=result.updated_at.isoformat(),
        change_id=result.change_id,
        backup_path=result.backup_path,
    )
