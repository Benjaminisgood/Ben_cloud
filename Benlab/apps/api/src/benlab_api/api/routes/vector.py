"""Vector search / RAG endpoints (Benlab keyword backend)."""

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from ...db.session import get_db
from ...models import Member
from ...services.vector_service import (
    VectorServiceError,
    build_chat_response,
    build_meta_response,
    build_rebuild_response,
)
from ..deps import require_api_admin, require_api_user

router = APIRouter(tags=["vector"])


@router.post("/vector/chat")
async def vector_chat(
    request: Request,
    user: Member = Depends(require_api_user),
    db: Session = Depends(get_db),
):
    try:
        body = await request.json()
    except Exception:
        body = {}
    try:
        return build_chat_response(db, user, body)
    except VectorServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail)


@router.post("/vector/rebuild")
async def rebuild_vector(
    request: Request,
    user: Member = Depends(require_api_admin),
    db: Session = Depends(get_db),
):
    try:
        body = await request.json()
    except Exception:
        body = {}
    try:
        return build_rebuild_response(db, body)
    except VectorServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail)


@router.get("/vector/meta")
def vector_meta(
    user: Member = Depends(require_api_user),
    db: Session = Depends(get_db),
):
    try:
        return build_meta_response(db)
    except VectorServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail)
