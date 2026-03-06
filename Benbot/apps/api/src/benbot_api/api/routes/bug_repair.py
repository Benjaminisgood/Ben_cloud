"""Bug 修复相关的 API 路由"""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.orm import Session

from ...db.session import get_db
from ...schemas.bug_repair import (
    BackupItem,
    RepairCompleteResponse,
    RepairPrepareResponse,
    UnrepairedBugItem,
)
from ...schemas.web import ApiTokenUserDTO
from ...services import bug_repair
from ...services.backup import backup_project_files, get_backup_history
from ...services.logs import add_log
from ...web.deps import AdminPrincipalDTO, require_admin_principal_or_401

router = APIRouter(tags=["bug-repair"])


def _request_ip(request: Request) -> str:
    return request.client.host if request.client else "unknown"


def _audit_access(
    db: Session,
    request: Request,
    user: AdminPrincipalDTO,
    *,
    action: str,
    bug_id: int | None = None,
) -> None:
    if not isinstance(user, ApiTokenUserDTO):
        return
    add_log(
        db,
        project_id="benbot",
        message=(
            f"[api-token] action={action} "
            f"bug_id={bug_id if bug_id is not None else '-'} "
            f"ip={_request_ip(request)}"
        ),
        level="INFO",
        source="authz",
    )


@router.get("/bugs/unrepaired", response_model=list[UnrepairedBugItem])
def get_unrepaired_bugs(request: Request, db: Session = Depends(get_db)):
    """Get approved bugs that haven't been repaired yet. Admin only."""
    user = require_admin_principal_or_401(request, db, required_scope="bug_repair:read")
    _audit_access(db, request, user, action="list_unrepaired")
    return bug_repair.get_unrepaired_bugs(db)


@router.post("/bugs/{bug_id}/prepare-repair", response_model=RepairPrepareResponse)
def prepare_repair(bug_id: int, request: Request, db: Session = Depends(get_db)):
    """
    Prepare for bug repair: create backup and log the repair start.
    This should be called before nanobot starts fixing the bug.
    Admin only.
    """
    user = require_admin_principal_or_401(request, db, required_scope="bug_repair:write")
    
    try:
        bug = bug_repair.require_approved_bug_for_repair(db, bug_id)
    except ValueError as exc:
        message = str(exc)
        if message == "Bug not found":
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=message) from exc
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=message) from exc
    
    # Create backup
    backup_path, backed_up_files = backup_project_files(bug.body)
    
    # Log repair start
    operation_id = bug_repair.log_repair_start(bug.body, backed_up_files)
    _audit_access(db, request, user, action="prepare_repair", bug_id=bug_id)

    return {
        "ok": True,
        "bug_id": bug_id,
        "backup_path": backup_path,
        "backed_up_files": backed_up_files,
        "bug_body": bug.body,
        "repair_log_operation_id": operation_id,
    }


@router.post("/bugs/{bug_id}/complete-repair", response_model=RepairCompleteResponse)
def complete_repair(
    bug_id: int,
    request: Request,
    changes: list[str] = Query(...),
    backup_location: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """
    Mark a bug repair as complete and log the changes.
    Admin only.
    """
    user = require_admin_principal_or_401(request, db, required_scope="bug_repair:write")
    
    try:
        bug = bug_repair.require_approved_bug_for_repair(db, bug_id)
    except ValueError as exc:
        message = str(exc)
        if message == "Bug not found":
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=message) from exc
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=message) from exc
    
    # Log repair completion
    operation_id = bug_repair.log_repair_complete(bug.body, changes, backup_location or "")
    bug = bug_repair.mark_bug_repaired(db, bug)
    _audit_access(db, request, user, action="complete_repair", bug_id=bug_id)

    return {
        "ok": True,
        "bug_id": bug_id,
        "repair_log_operation_id": operation_id,
        "repaired": bool(bug.repaired),
    }


@router.get("/backups", response_model=list[BackupItem])
def list_backups(request: Request, db: Session = Depends(get_db)):
    """List all backups. Admin only."""
    user = require_admin_principal_or_401(request, db, required_scope="bug_repair:read")
    _audit_access(db, request, user, action="list_backups")
    return get_backup_history()
