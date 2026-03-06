"""Vector search / RAG endpoints."""

from fastapi import APIRouter, Depends, HTTPException, Request

from ..deps import require_api_admin, require_api_user
from ...models import User
from ...services.vector_service import (
    VectorServiceError,
    build_chat_response,
    build_meta_response,
    build_rebuild_response,
)

router = APIRouter(tags=["vector"])


@router.post("/vector/chat")
async def vector_chat(
    request: Request,
    user: User = Depends(require_api_user),
):
    try:
        body = await request.json()
    except Exception:
        body = {}
    try:
        return build_chat_response(body)
    except VectorServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail)


@router.post("/vector/rebuild")
async def rebuild_vector(
    request: Request,
    user: User = Depends(require_api_admin),
):
    try:
        body = await request.json()
    except Exception:
        body = {}
    try:
        return build_rebuild_response(body)
    except VectorServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail)


@router.get("/vector/meta")
def vector_meta(user: User = Depends(require_api_user)):
    try:
        return build_meta_response()
    except VectorServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail)
