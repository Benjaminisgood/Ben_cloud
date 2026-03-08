"""Bencred configuration management."""
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
    APP_NAME: str = "Bencred"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = False

    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 9600

    # Database
    DATABASE_URL: str = f"sqlite+aiosqlite:///{(_DATA_DIR / 'bencred.db').resolve()}"

    # Security
    SECRET_KEY: str = "change-me-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days

    # SSO (Ben_cloud unified)
    SSO_SECRET: str = "change-me-to-bencloud-sso-secret"
    SSO_ENABLED: bool = True

    # Encryption for credentials
    FERNET_KEY: str = "change-me-to-32-byte-key-for-encryption"


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
