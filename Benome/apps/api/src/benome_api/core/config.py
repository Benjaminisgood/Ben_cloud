from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

_REPO_ROOT = Path(__file__).resolve().parents[5]
_DATA_DIR = _REPO_ROOT / "data"
_LOG_DIR = _REPO_ROOT / "logs"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(_REPO_ROOT / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    APP_NAME: str = "ling居家 API"
    APP_VERSION: str = "1.0.0"
    APP_ENV: str = "development"
    API_PREFIX: str = "/api"
    HOST: str = "0.0.0.0"
    PORT: int = 8200

    SECRET_KEY: str = "benome-dev-secret-key"
    DATABASE_URL: str = f"sqlite:///{_DATA_DIR / 'benome.sqlite'}"
    DB_BOOTSTRAP_CREATE_ALL: bool = False

    REMEMBER_DAYS: int = 30
    SESSION_COOKIE_NAME: str = "benome_session"
    SESSION_COOKIE_SAMESITE: str = "lax"
    SESSION_COOKIE_SECURE: bool = False

    ADMIN_USERNAME: str = "benbenbuben"
    ADMIN_PASSWORD: str = "benbenbuben"

    # SSO 共享密钥（必须与 Benbot 的 SSO_SECRET 一致）
    SSO_SECRET: str = "benbot-sso-secret-2025"

    # Benbot 基础 URL（用于 SSO 跳转）
    BENBOT_BASE_URL: str = "http://localhost:80"

    # 阿里云 OSS（通过 .env 注入，代码中不写死）
    ALIYUN_OSS_ENDPOINT: str = ""
    ALIYUN_OSS_ACCESS_KEY_ID: str = ""
    ALIYUN_OSS_ACCESS_KEY_SECRET: str = ""
    ALIYUN_OSS_BUCKET: str = ""

    @property
    def REPO_ROOT(self) -> Path:
        return _REPO_ROOT

    @property
    def DATA_DIR(self) -> Path:
        return _DATA_DIR

    @property
    def LOG_DIR(self) -> Path:
        return _LOG_DIR

    @property
    def WEB_DIR(self) -> Path:
        return self.REPO_ROOT / "apps" / "web"

    @property
    def WEB_TEMPLATES_DIR(self) -> Path:
        return self.WEB_DIR / "templates"

    @property
    def WEB_STATIC_DIR(self) -> Path:
        return self.WEB_DIR / "static"

    def ensure_data_dirs(self) -> None:
        self.DATA_DIR.mkdir(parents=True, exist_ok=True)
        self.LOG_DIR.mkdir(parents=True, exist_ok=True)


@lru_cache
def get_settings() -> Settings:
    return Settings()
