from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# apps/api/src/benoss_api/core/config.py -> parents[5] = repo root
_REPO_ROOT = Path(__file__).resolve().parents[5]
_DATA_DIR = _REPO_ROOT / "data"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(_REPO_ROOT / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # App
    APP_NAME: str = "Benoss API"
    APP_VERSION: str = "2.5.1"
    APP_ENV: str = "development"
    API_PREFIX: str = "/api"
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # Core
    SECRET_KEY: str = "dev-secret-key"
    DATABASE_URL: str = f"sqlite:///{_DATA_DIR / 'benoss.sqlite'}"
    DB_BOOTSTRAP_CREATE_ALL: bool = False
    DB_AUTO_UPGRADE_ON_STARTUP: bool = True

    # Session
    REMEMBER_DAYS: int = 30
    SESSION_COOKIE_SAMESITE: str = "lax"
    SESSION_COOKIE_SECURE: bool = False

    # Admin bootstrap
    ADMIN_USERNAME: str = ""
    ADMIN_PASSWORD: str = ""

    # OSS (Aliyun)
    ALIYUN_OSS_ENDPOINT: str | None = None
    ALIYUN_OSS_ACCESS_KEY_ID: str | None = None
    ALIYUN_OSS_ACCESS_KEY_SECRET: str | None = None
    ALIYUN_OSS_BUCKET: str | None = None
    ALIYUN_OSS_PREFIX: str = "benoss"
    ALIYUN_OSS_PUBLIC_BASE_URL: str | None = None
    ALIYUN_OSS_ASSUME_PUBLIC: str = "0"

    OSS_DIRECT_UPLOAD_ENABLED: str = "1"
    OSS_DIRECT_UPLOAD_EXPIRES_SECONDS: int = 900
    OSS_DIRECT_UPLOAD_TOKEN_MAX_AGE_SECONDS: int = 1800
    OSS_REMOTE_FAILOVER_LOCAL: str = "1"

    MAX_CONTENT_LENGTH: int = 1024 * 1024 * 1024

    # Board
    BOARD_DEFAULT_DAYS: int = 7
    BOARD_TOP_TAGS_DAYS: int = 0
    BOARD_TOP_TAGS_LIMIT: int = 10

    # AI
    AI_CHAT_PROVIDER: str = ""
    AI_EMBEDDING_PROVIDER: str = ""
    AI_TTS_PROVIDER: str = ""
    AI_IMAGE_PROVIDER: str = ""
    AI_REQUEST_TIMEOUT_SECONDS: int = 45
    AI_MAX_NOTICE_RECORDS: int = 180
    AI_NOTICE_CONTEXT_MAX_CHARS: int = 60000
    AI_NOTICE_RECORD_MAX_CHARS: int = 3200
    AI_NOTICE_FILE_READ_MAX_BYTES: int = 524288
    AI_NOTICE_ATTACH_IMAGES: str = "1"
    AI_NOTICE_MAX_IMAGE_ATTACHMENTS: int = 6
    AI_NOTICE_IMAGE_URL_EXPIRES_SECONDS: int = 1800
    AI_ARCHIVE_MULTIMODAL_PARSE: str = "1"
    AI_ARCHIVE_PARSE_MAX_CHARS: int = 8000
    AI_ARCHIVE_PARSE_TIMEOUT_SECONDS: int = 90
    AI_TTS_VOICE: str = "alloy"
    AI_TTS_RESPONSE_FORMAT: str = "mp3"
    AI_TTS_MAX_INPUT_CHARS: int = 3600
    AI_TTS_FALLBACK_LOCAL: str = "1"
    AI_IMAGE_FALLBACK_LOCAL: str = "1"
    PODCAST_DEFAULT_STYLE: str = "dialogue"

    # Archive / vector
    LOCAL_DAILY_ARCHIVE_DIR: str = str(_DATA_DIR / "daily-archive")
    LOCAL_VECTOR_STORE_DIR: str = str(_DATA_DIR / "vector-store")
    VECTOR_AUTO_REBUILD: str = "1"
    VECTOR_TOP_K: int = 6
    VECTOR_MAX_DOCS: int = 4000
    VECTOR_EMBEDDING_BATCH_SIZE: int = 16
    VECTOR_EMBEDDING_MAX_INPUT_CHARS: int = 4000
    HOME_AUTO_BUILD_DAILY_ASSETS: str = "1"
    HOME_DIGEST_RETRY_MINUTES: int = 30
    DIGEST_TIMEZONE: str = "Asia/Shanghai"
    ARCHIVE_RETENTION_DAYS: int = 7
    ARCHIVE_STORE_FILE_BLOB: str = "1"

    # AI providers
    CHAT_ANYWHERE_API_KEY: str | None = None
    CHAT_ANYWHERE_API_BASE_URL: str = "https://api.chatanywhere.tech/v1"
    CHAT_ANYWHERE_CHAT_MODEL: str = "gpt-4o-mini"
    CHAT_ANYWHERE_EMBEDDING_MODEL: str = "text-embedding-3-small"
    CHAT_ANYWHERE_TTS_MODEL: str = "gpt-4o-mini-tts"
    CHAT_ANYWHERE_IMAGE_MODEL: str = "gpt-image-1"
    CHAT_ANYWHERE_TRANSCRIBE_MODEL: str = "whisper-1"

    DEEPSEEK_API_KEY: str | None = None
    DEEPSEEK_API_BASE_URL: str = "https://api.deepseek.com/v1"
    DEEPSEEK_CHAT_MODEL: str = "deepseek-chat"
    DEEPSEEK_EMBEDDING_MODEL: str = "unsupported"
    DEEPSEEK_TTS_MODEL: str = "unsupported"
    DEEPSEEK_IMAGE_MODEL: str = "unsupported"
    DEEPSEEK_TRANSCRIBE_MODEL: str = "unsupported"

    ALIYUN_AI_API_KEY: str | None = None
    ALIYUN_AI_API_BASE_URL: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    ALIYUN_AI_CHAT_MODEL: str = "qwen-plus"
    ALIYUN_AI_EMBEDDING_MODEL: str = "text-embedding-v3"
    ALIYUN_AI_TTS_MODEL: str = "qwen3-tts-instruct-flash"
    ALIYUN_AI_IMAGE_MODEL: str = "qwen-image-max"
    ALIYUN_AI_TRANSCRIBE_MODEL: str = "whisper-1"

    OPENAI_API_KEY: str | None = None
    OPENAI_API_BASE_URL: str = "https://api.openai.com/v1"
    OPENAI_CHAT_MODEL: str = "gpt-4o-mini"
    OPENAI_EMBEDDING_MODEL: str = "text-embedding-3-small"
    OPENAI_TTS_MODEL: str = "gpt-4o-mini-tts"
    OPENAI_IMAGE_MODEL: str = "gpt-image-1"
    OPENAI_TRANSCRIBE_MODEL: str = "whisper-1"

    @property
    def REPO_ROOT(self) -> Path:
        return _REPO_ROOT

    @property
    def DATA_DIR(self) -> Path:
        return _DATA_DIR

    @property
    def WEB_DIR(self) -> Path:
        return self.REPO_ROOT / "apps" / "web"

    @property
    def WEB_TEMPLATES_DIR(self) -> Path:
        return self.WEB_DIR / "templates"

    @property
    def WEB_STATIC_DIR(self) -> Path:
        return self.WEB_DIR / "static"

    @property
    def OSS_ENDPOINT(self) -> str | None:
        return self.ALIYUN_OSS_ENDPOINT

    @property
    def OSS_ACCESS_KEY_ID(self) -> str | None:
        return self.ALIYUN_OSS_ACCESS_KEY_ID

    @property
    def OSS_ACCESS_KEY_SECRET(self) -> str | None:
        return self.ALIYUN_OSS_ACCESS_KEY_SECRET

    @property
    def OSS_BUCKET(self) -> str | None:
        return self.ALIYUN_OSS_BUCKET

    @property
    def OSS_PREFIX(self) -> str:
        return str(self.ALIYUN_OSS_PREFIX or "benoss").strip("/") or "benoss"

    @property
    def OSS_PUBLIC_BASE_URL(self) -> str | None:
        return self.ALIYUN_OSS_PUBLIC_BASE_URL

    @property
    def OSS_LOCAL_DIR(self) -> str:
        return str(_DATA_DIR / "oss-local")

    @property
    def UPLOAD_TMP_DIR(self) -> str:
        return str(_DATA_DIR / "uploads")

    def ensure_data_dirs(self) -> None:
        for d in [
            _DATA_DIR,
            _DATA_DIR / "oss-local",
            _DATA_DIR / "uploads",
            _DATA_DIR / "daily-archive",
            _DATA_DIR / "vector-store",
        ]:
            d.mkdir(parents=True, exist_ok=True)


@lru_cache
def get_settings() -> Settings:
    return Settings()
