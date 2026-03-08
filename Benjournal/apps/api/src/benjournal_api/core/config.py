
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

    APP_NAME: str = "Benjournal"
    APP_VERSION: str = "0.1.0"
    APP_ENV: str = "development"
    API_PREFIX: str = "/api"
    HOST: str = "0.0.0.0"
    PORT: int = 9200

    SECRET_KEY: str = "dev-only-change-me"
    SSO_SECRET: str = "dev-sso-secret-change-me"
    REMEMBER_DAYS: int = 30
    SESSION_COOKIE_NAME: str = "benjournal_session"
    SESSION_COOKIE_SAMESITE: str = "lax"
    SESSION_COOKIE_SECURE: bool = False

    ADMIN_USERNAME: str = "benbenbuben"
    ADMIN_PASSWORD: str = "benbenbuben"
    BENBOT_BASE_URL: str = "http://localhost:80"

    DATABASE_URL: str = f"sqlite:///{(_DATA_DIR / 'benjournal.sqlite').resolve()}"
    AUDIO_SEGMENTS_DIR: Path = _DATA_DIR / "audio_segments"
    COMBINED_AUDIO_DIR: Path = _DATA_DIR / "audio_combined"
    LOCAL_ARCHIVE_DIR: Path = _DATA_DIR / "local_oss"

    MAX_AUDIO_FILE_SIZE_MB: int = 64
    SUPPORTED_AUDIO_EXTENSIONS: str = "wav,webm,m4a,mp3,mp4,ogg"

    STORAGE_PROVIDER: str = "local"
    OSS_OBJECT_PREFIX: str = "journal"
    ALIYUN_OSS_ENDPOINT: str = ""
    ALIYUN_OSS_BUCKET: str = ""
    ALIYUN_OSS_ACCESS_KEY_ID: str = ""
    ALIYUN_OSS_ACCESS_KEY_SECRET: str = ""
    ALIYUN_OSS_PUBLIC_BASE_URL: str = ""

    STT_PROVIDER: str = "mock"
    STT_OPENAI_API_KEY: str = ""
    STT_OPENAI_MODEL: str = ""
    STT_OPENAI_BASE_URL: str = "https://api.openai.com/v1"
    STT_OPENAI_PROMPT: str = ""

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
    def supported_audio_extensions(self) -> set[str]:
        return {
            item.strip().lower()
            for item in self.SUPPORTED_AUDIO_EXTENSIONS.split(",")
            if item.strip()
        }

    def ensure_data_dirs(self) -> None:
        for path in (
            self.DATA_DIR,
            self.LOGS_DIR,
            self.AUDIO_SEGMENTS_DIR,
            self.COMBINED_AUDIO_DIR,
            self.LOCAL_ARCHIVE_DIR,
        ):
            path.mkdir(parents=True, exist_ok=True)


@lru_cache
def get_settings() -> Settings:
    return Settings()
