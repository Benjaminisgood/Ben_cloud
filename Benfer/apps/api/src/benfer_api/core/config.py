from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

from pydantic_settings import BaseSettings, SettingsConfigDict

_REPO_ROOT = Path(__file__).resolve().parents[5]
_DATA_DIR = _REPO_ROOT / "data"
_DEFAULT_DB_PATH = _DATA_DIR / "benfer.db"
_DEFAULT_CLIPBOARD_DIR = _DATA_DIR / "clipboard"


def _resolve_path(raw_path: str) -> Path:
    path = Path(raw_path).expanduser()
    if path.is_absolute():
        return path
    return (_REPO_ROOT / path).resolve()


def _sqlite_path_from_url(database_url: str) -> Path | None:
    prefix = "sqlite:///"
    if not database_url.startswith(prefix):
        return None
    raw = database_url[len(prefix):]
    if raw.startswith("/"):
        return Path(raw)
    return (_REPO_ROOT / raw).resolve()


def _resolve_database_url(database_url: str) -> str:
    sqlite_path = _sqlite_path_from_url(database_url)
    if sqlite_path is None:
        return database_url
    return f"sqlite:///{sqlite_path}"


@dataclass
class ProjectConfig:
    id: str
    name: str
    description: str
    icon: str
    port: int
    internal_url: str
    public_url: str
    health_endpoint: str
    requires_auth: bool = True


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=str(_REPO_ROOT / ".env"), case_sensitive=False)

    # Server
    PORT: int = 8500
    HOST: str = "0.0.0.0"

    # Database
    DATABASE_URL: str = f"sqlite:///{_DEFAULT_DB_PATH}"

    # Aliyun OSS
    ALIYUN_OSS_ENDPOINT: str = "oss-cn-shanghai.aliyuncs.com"
    ALIYUN_OSS_ACCESS_KEY_ID: str = ""
    ALIYUN_OSS_ACCESS_KEY_SECRET: str = ""
    ALIYUN_OSS_BUCKET: str = "00ling"
    ALIYUN_OSS_PREFIX: str = "benfer"

    # SSO
    SSO_SECRET: str = "benbot-sso-secret-2025"

    # Local Clipboard
    CLIPBOARD_STORAGE_PATH: str = str(_DEFAULT_CLIPBOARD_DIR)

    # File Expiration
    FILE_EXPIRATION_HOURS: int = 24

    # API Token
    NANOBOT_API_TOKEN: str = "nanobot-auto-repair-token-2026"

    # Benfer Session
    SESSION_TOKEN_TTL_SECONDS: int = 43200

    # CORS / Host hardening
    CORS_ALLOWED_ORIGINS: str = "http://localhost:8500,http://127.0.0.1:8500"
    ALLOWED_HOSTS: str = "localhost,127.0.0.1,0.0.0.0,00ling.com,testserver"

    # Upload and content guardrails
    PRESIGNED_URL_EXPIRES_SECONDS: int = 3600
    MAX_FILE_SIZE_BYTES: int = 5368709120  # 5 GiB
    MAX_CLIPBOARD_CHARS: int = 200000
    ALLOWED_FILE_CONTENT_TYPES: str = (
        "text/plain,text/csv,application/json,application/pdf,application/zip,"
        "application/octet-stream,image/*,video/*"
    )

    def model_post_init(self, __context: Any) -> None:
        self.DATABASE_URL = _resolve_database_url(self.DATABASE_URL)
        self.CLIPBOARD_STORAGE_PATH = str(_resolve_path(self.CLIPBOARD_STORAGE_PATH))

    def ensure_runtime_dirs(self) -> None:
        self.clipboard_storage_path.mkdir(parents=True, exist_ok=True)
        sqlite_path = _sqlite_path_from_url(self.DATABASE_URL)
        if sqlite_path is not None:
            sqlite_path.parent.mkdir(parents=True, exist_ok=True)

    @property
    def clipboard_storage_path(self) -> Path:
        return Path(self.CLIPBOARD_STORAGE_PATH)

    @property
    def cors_allowed_origins(self) -> list[str]:
        return [item.strip() for item in self.CORS_ALLOWED_ORIGINS.split(",") if item.strip()]

    @property
    def allowed_hosts(self) -> list[str]:
        return [item.strip() for item in self.ALLOWED_HOSTS.split(",") if item.strip()]

    @property
    def allowed_file_content_types(self) -> list[str]:
        return [item.strip().lower() for item in self.ALLOWED_FILE_CONTENT_TYPES.split(",") if item.strip()]

    @property
    def project_config(self) -> ProjectConfig:
        return ProjectConfig(
            id="benfer",
            name="Benfer",
            description="剪贴板与文件中转站",
            icon="📋",
            port=self.PORT,
            internal_url=f"http://localhost:{self.PORT}",
            public_url=f"http://00ling.com:{self.PORT}",
            health_endpoint="/health",
            requires_auth=True
        )


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    settings.ensure_runtime_dirs()
    return settings
