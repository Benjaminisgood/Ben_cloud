"""Minimal web UI for Benlink review workflow."""
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.templating import Jinja2Templates

from benlink_api.api.links import get_link_service
from benlink_api.services.link import LinkService

WEB_DIR = Path(__file__).resolve().parents[3] / "web"
TEMPLATES_DIR = WEB_DIR / "templates"
STATIC_DIR = WEB_DIR / "static"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

router = APIRouter(tags=["web"])


@router.get("/", name="dashboard")
async def dashboard(
    request: Request,
    view: str = Query("pending"),
    category: str | None = Query(None),
    service: LinkService = Depends(get_link_service),
):
    """Render the review-oriented link dashboard."""
    active_view = view if view in {"pending", "approved", "rejected", "archived"} else "pending"
    pending_items, pending_total = await service.list_links(
        page=1,
        page_size=24,
        category=category,
        review_status="pending",
    )
    approved_items, approved_total = await service.list_links(
        page=1,
        page_size=24,
        category=category,
        review_status="approved",
    )
    rejected_items, rejected_total = await service.list_links(
        page=1,
        page_size=12,
        category=category,
        review_status="rejected",
    )
    archive_items, archive_total = await service.list_links(
        page=1,
        page_size=12,
        category=category,
        review_status="archived",
    )
    section_map = {
        "pending": pending_items,
        "approved": approved_items,
        "rejected": rejected_items,
        "archived": archive_items,
    }

    return templates.TemplateResponse(
        name="dashboard.html",
        request=request,
        context={
            "request": request,
            "active_view": active_view,
            "current_items": section_map[active_view],
            "pending_items": pending_items,
            "approved_items": approved_items,
            "counts": {
                "pending": pending_total,
                "approved": approved_total,
                "rejected": rejected_total,
                "archived": archive_total,
            },
        },
    )


@router.get("/links/{link_id}", name="link_detail")
async def link_detail(
    request: Request,
    link_id: int,
    service: LinkService = Depends(get_link_service),
):
    """Render a link detail page."""
    try:
        link = await service.get_link(link_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))

    return templates.TemplateResponse(
        name="detail.html",
        request=request,
        context={
            "request": request,
            "link": link,
        },
    )
