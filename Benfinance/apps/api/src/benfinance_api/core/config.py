
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

_REPO_ROOT = Path(__file__).resolve().parents[5]
_WORKSPACE_ROOT = _REPO_ROOT.parent
_DATA_DIR = _REPO_ROOT / "data"
_LOGS_DIR = _REPO_ROOT / "logs"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(_REPO_ROOT / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    APP_NAME: str = "Benfinance"
    APP_VERSION: str = "0.1.0"
    APP_ENV: str = "development"
    API_PREFIX: str = "/api"
    HOST: str = "0.0.0.0"
    PORT: int = 9100

    SECRET_KEY: str = "dev-only-change-me"
    SSO_SECRET: str = "dev-sso-secret-change-me"
    REMEMBER_DAYS: int = 30
    SESSION_COOKIE_NAME: str = "benfinance_session"
    SESSION_COOKIE_SAMESITE: str = "lax"
    SESSION_COOKIE_SECURE: bool = False

    ADMIN_USERNAME: str = "benbenbuben"
    ADMIN_PASSWORD: str = "benbenbuben"
    BENBOT_BASE_URL: str = "http://localhost:80"

    DATABASE_URL: str = f"sqlite:///{(_DATA_DIR / 'benfinance.sqlite').resolve()}"
    SOURCE_DATABASE_PATH: Path = Field(default=_WORKSPACE_ROOT / "database" / "finance.db")

    STATIC_DIR: Path = _REPO_ROOT / "apps" / "web" / "static"
    TEMPLATES_DIR: Path = _REPO_ROOT / "apps" / "web" / "templates"
    LOGS_DIR: Path = _LOGS_DIR

    @property
    def REPO_ROOT(self) -> Path:
        return _REPO_ROOT

    @property
    def DATA_DIR(self) -> Path:
        return _DATA_DIR

    def ensure_data_dirs(self) -> None:
        for path in (self.DATA_DIR, self.LOGS_DIR):
            path.mkdir(parents=True, exist_ok=True)


@lru_cache
def get_settings() -> Settings:
    return Settings()
