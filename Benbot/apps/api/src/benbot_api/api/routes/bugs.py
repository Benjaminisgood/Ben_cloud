from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, field_validator
from sqlalchemy.orm import Session

from ...db.session import get_db
from ...schemas.bugs import BugActionResponse, BugItem, BugSubmitResponse
from ...services import bugs as bug_service
from ...web.deps import require_admin_session_user_or_403, require_session_user_or_401

router = APIRouter(tags=["bugs"])


class BugSubmitPayload(BaseModel):
    body: str

    @field_validator("body")
    @classmethod
    def body_not_empty(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("描述不能为空")
        if len(v) > 5000:
            raise ValueError("描述过长（最多 5000 字符）")
        return v


@router.post("/bugs", status_code=status.HTTP_201_CREATED, response_model=BugSubmitResponse)
def submit_bug(
    payload: BugSubmitPayload,
    request: Request,
    db: Session = Depends(get_db),
):
    """Submit a new bug report. Requires login."""
    user = require_session_user_or_401(request, db, detail="请先登录后再提交反馈")
    bug = bug_service.create_bug(db, reporter_id=user.id, body=payload.body)
    return {"ok": True, "id": bug.id}


@router.get("/bugs/pending", response_model=list[BugItem])
def get_pending_bugs(request: Request, db: Session = Depends(get_db)):
    """Get all pending bug reports. Admin only."""
    require_admin_session_user_or_403(request, db)
    return bug_service.list_pending(db)


@router.get("/bugs/approved", response_model=list[BugItem])
def get_approved_bugs(request: Request, db: Session = Depends(get_db)):
    """Get all approved bug reports. Requires login."""
    require_session_user_or_401(request, db)
    return bug_service.list_approved(db)


@router.get("/bugs/archived", response_model=list[BugItem])
def get_archived_bugs(request: Request, db: Session = Depends(get_db)):
    """Get all archived bug reports. Admin only."""
    require_admin_session_user_or_403(request, db)
    return bug_service.list_archived(db)


@router.post("/bugs/{bug_id}/approve", response_model=BugActionResponse)
def approve_bug(bug_id: int, request: Request, db: Session = Depends(get_db)):
    """Approve a bug report and write it to bug.md. Admin only."""
    require_admin_session_user_or_403(request, db)
    try:
        result = bug_service.approve_bug(db, bug_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return {"ok": True, "bug": result}


@router.post("/bugs/{bug_id}/reject", response_model=BugActionResponse)
def reject_bug(bug_id: int, request: Request, db: Session = Depends(get_db)):
    """Reject a pending bug report. Admin only."""
    require_admin_session_user_or_403(request, db)
    try:
        result = bug_service.reject_bug(db, bug_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return {"ok": True, "bug": result}


@router.post("/bugs/{bug_id}/archive", response_model=BugActionResponse)
def archive_bug(bug_id: int, request: Request, db: Session = Depends(get_db)):
    """Archive an approved bug after manual repair is complete. Admin only."""
    require_admin_session_user_or_403(request, db)
    try:
        result = bug_service.archive_bug(db, bug_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return {"ok": True, "bug": result}


@router.post("/bugs/{bug_id}/verify", response_model=BugActionResponse)
def verify_bug(bug_id: int, request: Request, db: Session = Depends(get_db)):
    """Verify a bug as fixed by admin. Admin only."""
    require_admin_session_user_or_403(request, db)
    try:
        result = bug_service.verify_bug(db, bug_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return {"ok": True, "bug": result}


@router.post("/bugs/{bug_id}/reopen", response_model=BugActionResponse)
def reopen_bug(bug_id: int, request: Request, db: Session = Depends(get_db)):
    """Reopen a bug that was marked as repaired but still has issues. Admin only."""
    require_admin_session_user_or_403(request, db)
    try:
        result = bug_service.reopen_bug(db, bug_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return {"ok": True, "bug": result}
