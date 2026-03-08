"""Link API routes."""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from benlink_api.db.session import get_db
from benlink_api.repositories.link import LinkRepository
from benlink_api.services.link import LinkService
from benlink_api.schemas.link import (
    LinkCreate,
    LinkListResponse,
    LinkResponse,
    LinkReview,
    LinkUpdate,
)

router = APIRouter(prefix="/links", tags=["links"])


def get_link_service(
    session: AsyncSession = Depends(get_db),
) -> LinkService:
    """Dependency to get link service."""
    repository = LinkRepository(session)
    return LinkService(repository)


@router.post("", response_model=LinkResponse, status_code=201)
async def create_link(
    data: LinkCreate,
    fetch_metadata: bool = Query(True, description="Automatically fetch metadata from URL"),
    service: LinkService = Depends(get_link_service),
) -> LinkResponse:
    """Create a new link. Optionally fetch Open Graph metadata from URL. Returns ID for audit trail."""
    try:
        return await service.create_link(data, fetch_metadata=fetch_metadata)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("", response_model=LinkListResponse)
async def list_links(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    category: str | None = Query(None, description="Filter by category"),
    status: str | None = Query(None, description="Filter by status: unread, reading, read, archived"),
    is_favorite: bool | None = Query(None, description="Filter by favorite status"),
    tag: str | None = Query(None, description="Filter by tag"),
    review_status: str | None = Query(None, description="Filter by review status"),
    source: str | None = Query(None, description="Filter by record source"),
    service: LinkService = Depends(get_link_service),
) -> LinkListResponse:
    """List links with pagination and filtering."""
    links, total = await service.list_links(
        page=page,
        page_size=page_size,
        category=category,
        status=status,
        is_favorite=is_favorite,
        tag=tag,
        review_status=review_status,
        source=source,
    )
    return LinkListResponse(
        items=links,
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{link_id}", response_model=LinkResponse)
async def get_link(
    link_id: int,
    service: LinkService = Depends(get_link_service),
) -> LinkResponse:
    """Get link by ID."""
    try:
        return await service.get_link(link_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.put("/{link_id}", response_model=LinkResponse)
async def update_link(
    link_id: int,
    data: LinkUpdate,
    service: LinkService = Depends(get_link_service),
) -> LinkResponse:
    """Update link."""
    try:
        return await service.update_link(link_id, data)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.delete("/{link_id}", status_code=204)
async def delete_link(
    link_id: int,
    service: LinkService = Depends(get_link_service),
) -> None:
    """Delete link."""
    deleted = await service.delete_link(link_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Link not found")


@router.post("/{link_id}/refresh", response_model=LinkResponse)
async def refresh_metadata(
    link_id: int,
    service: LinkService = Depends(get_link_service),
) -> LinkResponse:
    """Refresh metadata (title, description, og_image) from URL."""
    try:
        return await service.refresh_metadata(link_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/{link_id}/favorite", response_model=LinkResponse)
async def mark_favorite(
    link_id: int,
    is_favorite: bool = Query(True, description="Set favorite status"),
    service: LinkService = Depends(get_link_service),
) -> LinkResponse:
    """Mark link as favorite or unfavorite."""
    try:
        return await service.mark_favorite(link_id, is_favorite)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/{link_id}/status", response_model=LinkResponse)
async def update_status(
    link_id: int,
    status: str = Query(..., description="Status: unread, reading, read, archived"),
    service: LinkService = Depends(get_link_service),
) -> LinkResponse:
    """Update link reading status."""
    try:
        return await service.update_status(link_id, status)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{link_id}/review", response_model=LinkResponse)
async def review_link(
    link_id: int,
    data: LinkReview,
    service: LinkService = Depends(get_link_service),
) -> LinkResponse:
    """Review and approve/reject a link submission."""
    try:
        return await service.review_link(link_id, data)
    except ValueError as e:
        status_code = 404 if "not found" in str(e).lower() else 400
        raise HTTPException(status_code=status_code, detail=str(e))
