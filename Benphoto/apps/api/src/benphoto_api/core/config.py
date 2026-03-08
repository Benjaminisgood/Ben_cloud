
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

_REPO_ROOT = Path(__file__).resolve().parents[5]
_DATA_DIR = _REPO_ROOT / "data"
_LOGS_DIR = _REPO_ROOT / "logs"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(_REPO_ROOT / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    APP_NAME: str = "Benphoto"
    APP_VERSION: str = "0.1.0"
    APP_ENV: str = "development"
    API_PREFIX: str = "/api"
    HOST: str = "0.0.0.0"
    PORT: int = 9300

    SECRET_KEY: str = "dev-only-change-me"
    SSO_SECRET: str = "dev-sso-secret-change-me"
    REMEMBER_DAYS: int = 30
    SESSION_COOKIE_NAME: str = "benphoto_session"
    SESSION_COOKIE_SAMESITE: str = "lax"
    SESSION_COOKIE_SECURE: bool = False

    ADMIN_USERNAME: str = "benbenbuben"
    ADMIN_PASSWORD: str = "benbenbuben"
    BENBOT_BASE_URL: str = "http://localhost:80"

    DATABASE_URL: str = f"sqlite:///{(_DATA_DIR / 'benphoto.sqlite').resolve()}"
    DAILY_PHOTO_COUNT: int = 8
    TRASH_PREVIEW_LIMIT: int = 18
    ALIYUN_OSS_PUBLIC_BASE_URL: str = ""
    ALIYUN_OSS_ENDPOINT: str = ""
    ALIYUN_OSS_ACCESS_KEY_ID: str = ""
    ALIYUN_OSS_ACCESS_KEY_SECRET: str = ""
    ALIYUN_OSS_BUCKET: str = ""
    ALIYUN_OSS_PREFIX: str = ""
    ALIYUN_OSS_ALLOWED_EXTENSIONS: str = ".jpg,.jpeg,.png,.webp,.gif,.bmp,.heic,.heif"

    STATIC_DIR: Path = _REPO_ROOT / "apps" / "web" / "static"
    TEMPLATES_DIR: Path = _REPO_ROOT / "apps" / "web" / "templates"
    LOGS_DIR: Path = _LOGS_DIR

    @property
    def REPO_ROOT(self) -> Path:
        return _REPO_ROOT

    @property
    def DATA_DIR(self) -> Path:
        return _DATA_DIR

    @property
    def OSS_PREFIX(self) -> str:
        return self.ALIYUN_OSS_PREFIX.strip().strip("/")

    @property
    def OSS_PUBLIC_BASE_URL(self) -> str:
        endpoint = self.ALIYUN_OSS_ENDPOINT.strip().replace("https://", "").replace("http://", "").strip("/")
        bucket = self.ALIYUN_OSS_BUCKET.strip()
        if not endpoint or not bucket:
            return self.ALIYUN_OSS_PUBLIC_BASE_URL.strip().rstrip("/")

        base = f"https://{bucket}.{endpoint}"
        if self.OSS_PREFIX:
            return f"{base}/{self.OSS_PREFIX}"
        return base

    @property
    def OSS_ALLOWED_EXTENSIONS(self) -> tuple[str, ...]:
        normalized: list[str] = []
        for raw_value in self.ALIYUN_OSS_ALLOWED_EXTENSIONS.split(","):
            value = raw_value.strip().lower()
            if not value:
                continue
            normalized.append(value if value.startswith(".") else f".{value}")
        return tuple(dict.fromkeys(normalized))

    @property
    def OSS_SYNC_ENABLED(self) -> bool:
        return bool(
            self.ALIYUN_OSS_ENDPOINT.strip()
            and self.ALIYUN_OSS_ACCESS_KEY_ID.strip()
            and self.ALIYUN_OSS_ACCESS_KEY_SECRET.strip()
            and self.ALIYUN_OSS_BUCKET.strip()
            and self.OSS_ALLOWED_EXTENSIONS
        )

    def ensure_data_dirs(self) -> None:
        for path in (self.DATA_DIR, self.LOGS_DIR):
            path.mkdir(parents=True, exist_ok=True)


@lru_cache
def get_settings() -> Settings:
    return Settings()
