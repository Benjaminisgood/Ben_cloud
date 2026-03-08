"""Benlink configuration management."""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

_REPO_ROOT = Path(__file__).resolve().parents[5]
_DATA_DIR = _REPO_ROOT / "data"


class Settings(BaseSettings):
    """Application settings."""
    model_config = SettingsConfigDict(
        env_file=str(_REPO_ROOT / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # App
    APP_NAME: str = "Benlink"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = False

    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 9700

    # Database
    DATABASE_URL: str = f"sqlite+aiosqlite:///{(_DATA_DIR / 'benlink.db').resolve()}"

    # SSO (Ben_cloud unified)
    SSO_SECRET: str = "change-me-to-bencloud-sso-secret"
    SSO_ENABLED: bool = True

    # Link fetching
    FETCH_TIMEOUT: int = 10  # seconds
    MAX_REDIRECTS: int = 5


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
