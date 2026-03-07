from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from ...db.session import get_db
from ...schemas.user_access import (
    AccessProjectOption,
    AccessUserItem,
    UserProjectAccessOverviewResponse,
    UserProjectAccessUpdatePayload,
    UserProjectAccessUpdateResponse,
)
from ...services.project_access import (
    assemble_user_project_access_overview,
    update_user_project_access,
)
from ...web.deps import require_admin_session_user_or_403

router = APIRouter(prefix="/admin", tags=["admin-users"])


@router.get("/users/project-access", response_model=UserProjectAccessOverviewResponse)
def get_user_project_access_overview(request: Request, db: Session = Depends(get_db)):
    require_admin_session_user_or_403(request, db)
    overview = assemble_user_project_access_overview(db=db)
    all_project_ids = [project.id for project in overview.projects]
    return UserProjectAccessOverviewResponse(
        projects=[
            AccessProjectOption(id=project.id, name=project.name)
            for project in overview.projects
        ],
        users=[
            AccessUserItem(
                id=user.id,
                username=user.username,
                role=user.role,
                is_active=user.is_active,
                project_ids=all_project_ids if user.role == "admin" else overview.access_map.get(user.id, []),
            )
            for user in overview.users
        ],
    )


@router.put("/users/{user_id}/project-access", response_model=UserProjectAccessUpdateResponse)
def put_user_project_access(
    user_id: int,
    payload: UserProjectAccessUpdatePayload,
    request: Request,
    db: Session = Depends(get_db),
):
    operator = require_admin_session_user_or_403(request, db)

    try:
        _target_user, normalized_ids, change_id = update_user_project_access(
            db=db,
            operator=operator.username,
            user_id=user_id,
            project_ids=payload.project_ids,
        )
    except ValueError as exc:
        detail = str(exc)
        if detail == "user_not_found":
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=detail) from exc
        if detail == "admin_access_fixed":
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=detail) from exc
        if detail.startswith("invalid_project_ids:"):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=detail) from exc
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="bad_request") from exc

    return UserProjectAccessUpdateResponse(
        ok=True,
        user_id=user_id,
        project_ids=normalized_ids,
        change_id=change_id,
    )
