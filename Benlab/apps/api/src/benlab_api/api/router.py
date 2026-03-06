"""Top-level API router that aggregates all API sub-routers."""

from fastapi import APIRouter

from benlab_api.core.config import get_settings
from .routes import (
    account,
    admin,
    assets_generated,
    assets_jobs,
    board_details,
    board_summary,
    digest,
    echoes,
    home,
    notice_queries,
    notice_render,
    publications,
    records_comments,
    records_content,
    records_feed,
    records_mutations,
    records_tags,
    records_uploads,
    system,
    vector,
)

api_router = APIRouter(prefix=get_settings().API_PREFIX)
api_router.include_router(system.router)
api_router.include_router(account.router)
api_router.include_router(admin.router)
api_router.include_router(records_feed.router)
api_router.include_router(records_content.router)
api_router.include_router(records_comments.router)
api_router.include_router(records_tags.router)
api_router.include_router(records_mutations.router)
api_router.include_router(records_uploads.router)
api_router.include_router(board_summary.router)
api_router.include_router(board_details.router)
api_router.include_router(echoes.router)
api_router.include_router(notice_queries.router)
api_router.include_router(notice_render.router)
api_router.include_router(assets_generated.router)
api_router.include_router(assets_jobs.router)
api_router.include_router(digest.router)
api_router.include_router(home.router)
api_router.include_router(vector.router)
api_router.include_router(publications.router)
