"""Record tag query endpoints."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from ...db.session import get_db
from ...models import User
from ...repositories.records_repo import search_tags
from ..deps import require_api_user

router = APIRouter(tags=["records"])


@router.get("/tags")
def list_tags(
    q: str = Query(""),
    limit: int = Query(20, ge=1, le=100),
    user: User = Depends(require_api_user),
    db: Session = Depends(get_db),
):
    tags = search_tags(db, q=q, limit=limit)
    return {"items": [{"name": tag.name} for tag in tags]}
