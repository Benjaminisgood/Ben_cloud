from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from apps.api.router import api_router
from apps.api.routers.auth import router as auth_router
from apps.core.config import settings
from apps.db import create_all
from apps.services.auto_enrichment_scheduler import start_auto_enrichment_scheduler, stop_auto_enrichment_scheduler
from apps.services.task_queue import start_worker, stop_worker

app = FastAPI(title=settings.app_name, version=settings.app_version)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins or ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix=settings.api_prefix)
app.include_router(auth_router)  # No prefix for SSO auth

static_dir = Path(__file__).resolve().parent / "static"
app.mount("/static", StaticFiles(directory=static_dir), name="static")


@app.on_event("startup")
def on_startup() -> None:
    create_all()
    start_worker()
    start_auto_enrichment_scheduler()


@app.on_event("shutdown")
def on_shutdown() -> None:
    stop_auto_enrichment_scheduler()
    stop_worker()


@app.get("/")
def index() -> FileResponse:
    return FileResponse(static_dir / "index.html")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
