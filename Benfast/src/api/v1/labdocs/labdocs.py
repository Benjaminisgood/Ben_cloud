from __future__ import annotations

from fastapi import APIRouter, File, Query, UploadFile

from core.dependency import DependAuth
from models.admin import User
from schemas.base import Fail, Success
from schemas.labdocs import (
    BookCommentIn,
    BookCreateIn,
    BookLockIn,
    BookPageCreateIn,
    BookPageMoveIn,
    BookPageUpdateIn,
    BookPublishIn,
    BookUpdateIn,
)
from services.labdocs_service import (
    LockConflictError,
    PermissionDeniedError,
    ResourceNotFoundError,
    VersionConflictError,
    labdocs_service,
)

router = APIRouter(tags=["labdocs"])


def _user_ctx(current_user: User) -> dict[str, object]:
    return {
        "id": int(current_user.id),
        "username": current_user.username,
        "is_superuser": bool(current_user.is_superuser),
    }


@router.get("/books", summary="书籍列表")
async def list_books(
    current_user: User = DependAuth,
    q: str | None = Query(default=None),
):
    _ = current_user
    return Success(data=labdocs_service.list_books(q=q))


@router.post("/books", summary="创建书籍")
async def create_book(payload: BookCreateIn, current_user: User = DependAuth):
    user = _user_ctx(current_user)
    try:
        book = labdocs_service.create_book(
            title=payload.title,
            slug=payload.slug,
            description=payload.description,
            summary=payload.summary,
            keywords=payload.keywords,
            user_id=int(user["id"]),
            username=str(user["username"]),
        )
        return Success(data=book)
    except ValueError as exc:
        return Fail(code=400, msg=str(exc))


@router.get("/books/{book_id}", summary="书籍详情")
async def get_book(book_id: str, current_user: User = DependAuth):
    _ = current_user
    try:
        return Success(data=labdocs_service.get_book(book_id))
    except ResourceNotFoundError as exc:
        return Fail(code=404, msg=str(exc))


@router.put("/books/{book_id}", summary="更新书籍")
async def update_book(
    book_id: str,
    payload: BookUpdateIn,
    current_user: User = DependAuth,
):
    user = _user_ctx(current_user)
    try:
        book = labdocs_service.update_book(
            book_id,
            title=payload.title,
            slug=payload.slug,
            description=payload.description,
            summary=payload.summary,
            keywords=payload.keywords,
            user_id=int(user["id"]),
            username=str(user["username"]),
        )
        return Success(data=book)
    except ResourceNotFoundError as exc:
        return Fail(code=404, msg=str(exc))
    except ValueError as exc:
        return Fail(code=400, msg=str(exc))


@router.get("/books/{book_id}/tree", summary="书籍目录树")
async def get_book_tree(book_id: str, current_user: User = DependAuth):
    _ = current_user
    try:
        return Success(data=labdocs_service.get_book_tree(book_id))
    except ResourceNotFoundError as exc:
        return Fail(code=404, msg=str(exc))


@router.get("/books/{book_id}/references", summary="书籍引用索引")
async def get_book_references(
    book_id: str,
    current_user: User = DependAuth,
    page_id: str | None = Query(default=None),
    q: str | None = Query(default=None),
):
    _ = current_user
    try:
        return Success(data=labdocs_service.list_reference_targets(book_id, page_id=page_id, q=q))
    except ResourceNotFoundError as exc:
        return Fail(code=404, msg=str(exc))


@router.post("/books/{book_id}/pages", summary="新增页面")
async def create_page(
    book_id: str,
    payload: BookPageCreateIn,
    current_user: User = DependAuth,
):
    user = _user_ctx(current_user)
    try:
        page = labdocs_service.create_page(
            book_id,
            parent_id=payload.parent_id,
            title=payload.title,
            slug=payload.slug,
            kind=payload.kind,
            order=payload.order,
            content=payload.content,
            user_id=int(user["id"]),
            username=str(user["username"]),
        )
        return Success(data=page)
    except ResourceNotFoundError as exc:
        return Fail(code=404, msg=str(exc))
    except ValueError as exc:
        return Fail(code=400, msg=str(exc))


@router.get("/books/{book_id}/assets", summary="书籍附件列表")
async def list_book_assets(book_id: str, current_user: User = DependAuth):
    _ = current_user
    try:
        return Success(data=labdocs_service.list_book_assets(book_id))
    except ResourceNotFoundError as exc:
        return Fail(code=404, msg=str(exc))


@router.post("/books/{book_id}/assets", summary="上传书籍附件")
async def upload_book_asset(
    book_id: str,
    file: UploadFile = File(...),
    current_user: User = DependAuth,
):
    user = _user_ctx(current_user)
    try:
        payload = await file.read()
        asset = labdocs_service.upload_book_asset(
            book_id,
            filename=file.filename or "file",
            content_type=file.content_type,
            payload=payload,
            user_id=int(user["id"]),
            username=str(user["username"]),
        )
        return Success(data=asset)
    except ResourceNotFoundError as exc:
        return Fail(code=404, msg=str(exc))
    except ValueError as exc:
        return Fail(code=400, msg=str(exc))


@router.get("/pages/{page_id}", summary="页面详情")
async def get_page(page_id: str, current_user: User = DependAuth):
    _ = current_user
    try:
        return Success(data=labdocs_service.get_page(page_id))
    except ResourceNotFoundError as exc:
        return Fail(code=404, msg=str(exc))


@router.put("/pages/{page_id}", summary="更新页面")
async def update_page(
    page_id: str,
    payload: BookPageUpdateIn,
    current_user: User = DependAuth,
):
    user = _user_ctx(current_user)
    try:
        page = labdocs_service.update_page(
            page_id,
            expected_version=payload.expected_version,
            title=payload.title,
            slug=payload.slug,
            content=payload.content,
            change_note=payload.change_note,
            user_id=int(user["id"]),
            username=str(user["username"]),
            is_superuser=bool(user["is_superuser"]),
        )
        return Success(data=page)
    except ResourceNotFoundError as exc:
        return Fail(code=404, msg=str(exc))
    except VersionConflictError as exc:
        return Fail(code=409, msg=str(exc), current_version=exc.current_version)
    except LockConflictError as exc:
        return Fail(code=409, msg=str(exc), lock=exc.lock)
    except ValueError as exc:
        return Fail(code=400, msg=str(exc))


@router.post("/pages/{page_id}/move", summary="移动页面")
async def move_page(
    page_id: str,
    payload: BookPageMoveIn,
    current_user: User = DependAuth,
):
    _ = current_user
    try:
        return Success(
            data=labdocs_service.move_page(
                page_id,
                parent_id=payload.parent_id,
                order=payload.order,
            )
        )
    except ResourceNotFoundError as exc:
        return Fail(code=404, msg=str(exc))
    except ValueError as exc:
        return Fail(code=400, msg=str(exc))


@router.get("/pages/{page_id}/revisions", summary="页面修订历史")
async def list_page_revisions(
    page_id: str,
    current_user: User = DependAuth,
    limit: int = Query(default=50, ge=1, le=200),
):
    _ = current_user
    try:
        return Success(data=labdocs_service.list_page_revisions(page_id, limit=limit))
    except ResourceNotFoundError as exc:
        return Fail(code=404, msg=str(exc))


@router.get("/pages/{page_id}/comments", summary="页面评论")
async def list_page_comments(page_id: str, current_user: User = DependAuth):
    _ = current_user
    try:
        return Success(data=labdocs_service.list_page_comments(page_id))
    except ResourceNotFoundError as exc:
        return Fail(code=404, msg=str(exc))


@router.post("/pages/{page_id}/comments", summary="新增页面评论")
async def add_page_comment(
    page_id: str,
    payload: BookCommentIn,
    current_user: User = DependAuth,
):
    user = _user_ctx(current_user)
    try:
        return Success(
            data=labdocs_service.add_page_comment(
                page_id,
                content=payload.content,
                anchor=payload.anchor,
                user_id=int(user["id"]),
                username=str(user["username"]),
            )
        )
    except ResourceNotFoundError as exc:
        return Fail(code=404, msg=str(exc))


@router.get("/pages/{page_id}/lock", summary="查看页面编辑锁")
async def get_page_lock(page_id: str, current_user: User = DependAuth):
    _ = current_user
    try:
        return Success(data=labdocs_service.get_lock(page_id))
    except ResourceNotFoundError as exc:
        return Fail(code=404, msg=str(exc))


@router.post("/pages/{page_id}/lock/acquire", summary="获取页面编辑锁")
async def acquire_page_lock(
    page_id: str,
    payload: BookLockIn,
    current_user: User = DependAuth,
):
    user = _user_ctx(current_user)
    try:
        return Success(
            data=labdocs_service.acquire_lock(
                page_id,
                user_id=int(user["id"]),
                username=str(user["username"]),
                ttl_minutes=payload.ttl_minutes,
            )
        )
    except ResourceNotFoundError as exc:
        return Fail(code=404, msg=str(exc))
    except LockConflictError as exc:
        return Fail(code=409, msg=str(exc), lock=exc.lock)


@router.post("/pages/{page_id}/lock/release", summary="释放页面编辑锁")
async def release_page_lock(page_id: str, current_user: User = DependAuth):
    user = _user_ctx(current_user)
    try:
        return Success(
            data=labdocs_service.release_lock(
                page_id,
                user_id=int(user["id"]),
                is_superuser=bool(user["is_superuser"]),
            )
        )
    except ResourceNotFoundError as exc:
        return Fail(code=404, msg=str(exc))
    except PermissionDeniedError as exc:
        return Fail(code=403, msg=str(exc))


@router.post("/books/{book_id}/publish", summary="发布书籍")
async def publish_book(
    book_id: str,
    payload: BookPublishIn,
    current_user: User = DependAuth,
):
    user = _user_ctx(current_user)
    try:
        return Success(
            data=labdocs_service.publish_book(
                book_id,
                message=payload.message,
                user_id=int(user["id"]),
                username=str(user["username"]),
            )
        )
    except ResourceNotFoundError as exc:
        return Fail(code=404, msg=str(exc))
    except ValueError as exc:
        return Fail(code=400, msg=str(exc))


@router.get("/books/{book_id}/publishes", summary="发布记录")
async def list_publishes(book_id: str, current_user: User = DependAuth):
    _ = current_user
    try:
        return Success(data=labdocs_service.list_publishes(book_id))
    except ResourceNotFoundError as exc:
        return Fail(code=404, msg=str(exc))
