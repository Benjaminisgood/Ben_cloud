from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import AliasChoices, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# apps/api/src/benlab_api/core/config.py -> parents[5] = repo root
_REPO_ROOT = Path(__file__).resolve().parents[5]
_DATA_DIR = _REPO_ROOT / "data"
_LOGS_DIR = _REPO_ROOT / "logs"


def _normalize_repo_local_path(raw_value: str, *, app_name: str) -> str:
    candidate = Path(raw_value).expanduser()
    if not candidate.is_absolute():
        return str((_REPO_ROOT / candidate).resolve())

    parts = candidate.parts
    for idx in range(len(parts) - 1):
        if parts[idx].lower() == "ben_cloud" and parts[idx + 1].lower() == app_name.lower():
            suffix = Path(*parts[idx + 2 :])
            return str((_REPO_ROOT / suffix).resolve())
    return str(candidate)


def _normalize_sqlite_url(raw_url: str, *, app_name: str) -> str:
    prefix = "sqlite:///"
    if not raw_url.startswith(prefix):
        return raw_url
    path_value = raw_url[len(prefix) :]
    if path_value in {"", ":memory:"}:
        return raw_url
    normalized_path = _normalize_repo_local_path(path_value, app_name=app_name)
    return f"{prefix}{normalized_path}"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(_REPO_ROOT / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    APP_NAME: str = "Benlab"
    APP_VERSION: str = "1.0.0"
    APP_ENV: str = Field(default="development", alias="APP_ENV")
    API_PREFIX: str = Field(default="/api", alias="API_PREFIX")
    SECRET_KEY: str = Field(
        default="dev-only-change-me",
        validation_alias=AliasChoices("SECRET_KEY", "FLASK_SECRET_KEY"),
    )

    HOST: str = Field(default="0.0.0.0", validation_alias=AliasChoices("HOST", "FLASK_RUN_HOST"))
    PORT: int = Field(
        default=9000,
        validation_alias=AliasChoices("PORT", "UVICORN_PORT", "FLASK_RUN_PORT"),
    )

    DATABASE_URL: str = Field(
        default=f"sqlite:///{(_DATA_DIR / 'benlab.sqlite').resolve()}",
        validation_alias=AliasChoices("DATABASE_URL", "SQLALCHEMY_DATABASE_URI"),
    )
    DB_BOOTSTRAP_CREATE_ALL: bool = Field(default=False, alias="DB_BOOTSTRAP_CREATE_ALL")

    REMEMBER_DAYS: int = 30
    SESSION_COOKIE_SAMESITE: str = "lax"
    SESSION_COOKIE_SECURE: bool = False
    ADMIN_USERNAME: str = "admin"
    ADMIN_PASSWORD: str = "admin"

    STATIC_DIR: Path = Field(default=_REPO_ROOT / "apps" / "web" / "static", alias="STATIC_DIR")
    TEMPLATES_DIR: Path = Field(default=_REPO_ROOT / "apps" / "web" / "templates", alias="TEMPLATES_DIR")
    ATTACHMENTS_DIR: Path = Field(
        default=_DATA_DIR / "uploads",
        validation_alias=AliasChoices("ATTACHMENTS_DIR", "ATTACHMENTS_FOLDER"),
    )
    LOGS_DIR: Path = Field(default=_LOGS_DIR, alias="LOGS_DIR")

    EVENT_SHARE_TOKEN_SALT: str = Field(default="benlab-event-share", alias="EVENT_SHARE_TOKEN_SALT")
    EVENT_SHARE_TOKEN_MAX_AGE: int = Field(default=60 * 60 * 24 * 30, alias="EVENT_SHARE_TOKEN_MAX_AGE")

    DIRECT_OSS_UPLOAD_ENABLED: bool = Field(default=False, alias="DIRECT_OSS_UPLOAD_ENABLED")

    @field_validator("DATABASE_URL", mode="before")
    @classmethod
    def normalize_database_url(cls, v):
        if not isinstance(v, str) or not v.strip():
            return v
        return _normalize_sqlite_url(v.strip(), app_name="Benlab")

    @property
    def REPO_ROOT(self) -> Path:
        return _REPO_ROOT

    @property
    def DATA_DIR(self) -> Path:
        return _DATA_DIR

    def ensure_data_dirs(self) -> None:
        for path in (_DATA_DIR, self.ATTACHMENTS_DIR, self.LOGS_DIR):
            path.mkdir(parents=True, exist_ok=True)


@lru_cache
def get_settings() -> Settings:
    return Settings()
