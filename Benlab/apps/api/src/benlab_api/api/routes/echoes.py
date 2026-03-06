"""Echoes – mixed message + attachment stream."""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ...db.session import get_db
from ...models import Member
from ...repositories.echoes_api_repo import list_echo_assets, list_echo_records
from ...services.admin_identity import is_admin_member
from ...services.echoes_views import VALID_FILE_TYPES, build_echoes_response
from ..deps import require_api_user

router = APIRouter(tags=["echoes"])


@router.get("/echoes")
def get_echoes(
    file_type: str = Query(""),
    before_id: Optional[int] = Query(None),
    before_asset_id: Optional[int] = Query(None),
    limit: int = Query(20, ge=1, le=100),
    user: Member = Depends(require_api_user),
    db: Session = Depends(get_db),
):
    if file_type and file_type not in VALID_FILE_TYPES:
        raise HTTPException(status_code=400, detail="invalid file_type")

    records = list_echo_records(
        db,
        viewer_user_id=user.id,
        is_admin=is_admin_member(user),
        before_id=before_id,
        limit=limit,
    )
    assets = list_echo_assets(db, before_asset_id=before_asset_id, limit=limit)

    return build_echoes_response(
        records=records,
        assets=assets,
        viewer=user,
        file_type=file_type,
        limit=limit,
    )
