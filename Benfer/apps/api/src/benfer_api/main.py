from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pathlib import Path
import uvicorn

from benfer_api.core.config import get_settings
from benfer_api.db.database import init_db
from benfer_api.api.routes import files, auth

settings = get_settings()

app = FastAPI(
    title="Benfer API",
    description="剪贴板与文件中转站服务",
    version="1.0.0"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_allowed_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)

if settings.allowed_hosts and "*" not in settings.allowed_hosts:
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=settings.allowed_hosts,
    )

# Include routers
app.include_router(files.router, prefix="/api", tags=["files"])
app.include_router(auth.router, prefix="/auth", tags=["auth"])

# Mount static files and serve frontend
BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent
WEB_DIR = BASE_DIR / "web"
app.mount("/static", StaticFiles(directory=WEB_DIR / "static"), name="static")

@app.get("/")
async def serve_frontend():
    """Serve the frontend page"""
    return FileResponse(WEB_DIR / "index.html")

@app.on_event("startup")
async def startup_event():
    """Initialize database on startup"""
    init_db()
    print(f"Benfer service started on {settings.HOST}:{settings.PORT}")


@app.get("/health")
async def health():
    """Health check endpoint"""
    return {"status": "ok"}


# Remove the old root endpoint since we now serve frontend
# @app.get("/")
# async def root():
#     """Root endpoint"""
#     return {
#         "service": "Benfer",
#         "description": "剪贴板与文件中转站",
#         "docs": "/docs",
#         "health": "/health"
#     }


def run() -> None:
    uvicorn.run(
        "benfer_api.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=True
    )


if __name__ == "__main__":
    run()
