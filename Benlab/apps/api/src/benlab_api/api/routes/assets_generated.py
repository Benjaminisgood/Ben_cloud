"""Generated asset read endpoints (Benlab attachment-backed)."""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from sqlalchemy.orm import Session

from ...db.session import get_db
from ...models import Member
from ...repositories.assets_api_repo import get_generated_asset, list_ready_generated_assets
from ...services.assets_views import asset_payload, asset_visible, list_assets_response, parse_source_day, read_asset_blob
from ..deps import require_api_user

router = APIRouter(tags=["assets"])


@router.get("/generated-assets")
def list_generated_assets(
    kind: str = Query(""),
    source_day: str = Query(""),
    is_daily_digest: Optional[bool] = Query(None),
    before_id: Optional[int] = Query(None),
    limit: int = Query(20, ge=1, le=100),
    user: Member = Depends(require_api_user),
    db: Session = Depends(get_db),
):
    rows = list_ready_generated_assets(
        db,
        kind=kind,
        source_day=parse_source_day(source_day),
        is_daily_digest=is_daily_digest,
        before_id=before_id,
        limit=limit,
    )
    return list_assets_response(rows, limit=limit)


@router.get("/generated-assets/{asset_id}")
def get_generated_asset_detail(
    asset_id: int,
    user: Member = Depends(require_api_user),
    db: Session = Depends(get_db),
):
    asset = get_generated_asset(db, asset_id=asset_id)
    if not asset or not asset_visible(asset, viewer_user_id=user.id):
        raise HTTPException(status_code=404, detail="not found")
    return asset_payload(asset)


@router.get("/generated-assets/{asset_id}/blob")
def get_asset_blob(
    asset_id: int,
    user: Member = Depends(require_api_user),
    db: Session = Depends(get_db),
):
    asset = get_generated_asset(db, asset_id=asset_id)
    if not asset or not asset_visible(asset, viewer_user_id=user.id):
        raise HTTPException(status_code=404, detail="not found")
    try:
        data = read_asset_blob(asset)
    except Exception:
        raise HTTPException(status_code=404, detail="blob not found")
    return Response(content=data, media_type=asset_payload(asset).get("content_type") or "application/octet-stream")
