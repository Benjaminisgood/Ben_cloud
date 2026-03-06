from fastapi import APIRouter

from apps.api.routers.articles import router as articles_router
from apps.api.routers.auth import router as auth_router
from apps.api.routers.enrichment import router as enrichment_router
from apps.api.routers.health import router as health_router
from apps.api.routers.ingestion import router as ingestion_router
from apps.api.routers.providers import router as providers_router
from apps.api.routers.tags import router as tags_router
from apps.api.routers.tasks import router as tasks_router

api_router = APIRouter()
api_router.include_router(auth_router)
api_router.include_router(health_router)
api_router.include_router(providers_router)
api_router.include_router(ingestion_router)
api_router.include_router(enrichment_router)
api_router.include_router(articles_router)
api_router.include_router(tags_router)
api_router.include_router(tasks_router)
