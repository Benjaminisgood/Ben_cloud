"""Record tag query endpoints."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from ...db.session import get_db
from ...models import Member
from ...repositories.records_api_repo import list_tags
from ...services.admin_identity import is_admin_member
from ..deps import require_api_user

router = APIRouter(tags=["records"])


@router.get("/tags")
def list_tags_endpoint(
    q: str = Query(""),
    limit: int = Query(20, ge=1, le=100),
    user: Member = Depends(require_api_user),
    db: Session = Depends(get_db),
):
    tags = list_tags(db, viewer_id=user.id, is_admin=is_admin_member(user), q=q, limit=limit)
    return {"items": [{"name": tag} for tag in tags]}
