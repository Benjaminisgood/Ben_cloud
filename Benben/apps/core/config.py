from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[2]


def load_dotenv(path: Path) -> None:
    if not path.exists():
        return

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()
        if not key:
            continue
        if value.startswith(("\"", "'")) and value.endswith(("\"", "'")) and len(value) >= 2:
            value = value[1:-1]
        os.environ.setdefault(key, value)


def _parse_int(name: str, raw_value: str, *, minimum: int = 1) -> int:
    try:
        parsed = int(raw_value)
    except ValueError as exc:
        raise RuntimeError(f"环境变量 {name} 必须为整数") from exc
    if parsed < minimum:
        raise RuntimeError(f"环境变量 {name} 必须 >= {minimum}")
    return parsed


def _parse_bool(raw_value: str) -> bool:
    return raw_value.strip().lower() in {"1", "true", "yes", "on"}


def _resolve_path(raw_value: str, *, base: Path) -> Path:
    path = Path(raw_value).expanduser()
    if path.is_absolute():
        return path
    return (base / path).resolve()


@dataclass(frozen=True)
class Settings:
    app_name: str
    app_env: str
    host: str
    port: int

    oss_endpoint: str
    oss_access_key_id: str
    oss_access_key_secret: str
    oss_bucket_name: str
    oss_prefix: str

    sso_secret: str
    session_secret_key: str
    session_max_age_seconds: int
    session_cookie_secure: bool

    upload_max_bytes: int
    upload_max_requests_per_minute: int
    markdown_max_bytes: int

    default_project: str
    audit_log_path: Path
    audit_max_bytes: int

    @property
    def templates_dir(self) -> Path:
        return ROOT_DIR / "templates"

    @property
    def logs_dir(self) -> Path:
        return ROOT_DIR / "logs"

    @classmethod
    def from_env(cls) -> "Settings":
        required = {
            "BENBEN_OSS_ENDPOINT": os.getenv("BENBEN_OSS_ENDPOINT", "").strip(),
            "BENBEN_OSS_ACCESS_KEY_ID": os.getenv("BENBEN_OSS_ACCESS_KEY_ID", "").strip(),
            "BENBEN_OSS_ACCESS_KEY_SECRET": os.getenv("BENBEN_OSS_ACCESS_KEY_SECRET", "").strip(),
            "BENBEN_OSS_BUCKET_NAME": os.getenv("BENBEN_OSS_BUCKET_NAME", "").strip(),
            "BENBEN_SSO_SECRET": os.getenv("BENBEN_SSO_SECRET", "").strip(),
            "BENBEN_SESSION_SECRET_KEY": os.getenv("BENBEN_SESSION_SECRET_KEY", "").strip(),
        }
        missing = [name for name, value in required.items() if not value]
        if missing:
            raise RuntimeError(
                "缺少必需环境变量: " + ", ".join(missing) + "。请先配置 Benben/.env 后再启动。"
            )

        oss_prefix = os.getenv("BENBEN_OSS_PREFIX", "benben").strip().strip("/")
        if not oss_prefix:
            raise RuntimeError("环境变量 BENBEN_OSS_PREFIX 不能为空")

        audit_log_path = _resolve_path(
            os.getenv("BENBEN_AUDIT_LOG_PATH", "logs/benben_audit.log").strip() or "logs/benben_audit.log",
            base=ROOT_DIR,
        )

        return cls(
            app_name=os.getenv("BENBEN_APP_NAME", "Benben").strip() or "Benben",
            app_env=os.getenv("BENBEN_APP_ENV", "development").strip() or "development",
            host=os.getenv("BENBEN_HOST", "0.0.0.0").strip() or "0.0.0.0",
            port=_parse_int("BENBEN_PORT", os.getenv("BENBEN_PORT", "8600"), minimum=1),
            oss_endpoint=required["BENBEN_OSS_ENDPOINT"],
            oss_access_key_id=required["BENBEN_OSS_ACCESS_KEY_ID"],
            oss_access_key_secret=required["BENBEN_OSS_ACCESS_KEY_SECRET"],
            oss_bucket_name=required["BENBEN_OSS_BUCKET_NAME"],
            oss_prefix=oss_prefix,
            sso_secret=required["BENBEN_SSO_SECRET"],
            session_secret_key=required["BENBEN_SESSION_SECRET_KEY"],
            session_max_age_seconds=_parse_int(
                "BENBEN_SESSION_MAX_AGE_SECONDS",
                os.getenv("BENBEN_SESSION_MAX_AGE_SECONDS", "43200"),
                minimum=60,
            ),
            session_cookie_secure=_parse_bool(os.getenv("BENBEN_SESSION_COOKIE_SECURE", "false")),
            upload_max_bytes=_parse_int(
                "BENBEN_UPLOAD_MAX_BYTES",
                os.getenv("BENBEN_UPLOAD_MAX_BYTES", str(5 * 1024 * 1024)),
                minimum=1024,
            ),
            upload_max_requests_per_minute=_parse_int(
                "BENBEN_UPLOAD_MAX_REQUESTS_PER_MINUTE",
                os.getenv("BENBEN_UPLOAD_MAX_REQUESTS_PER_MINUTE", "20"),
                minimum=1,
            ),
            markdown_max_bytes=_parse_int(
                "BENBEN_MARKDOWN_MAX_BYTES",
                os.getenv("BENBEN_MARKDOWN_MAX_BYTES", str(1024 * 1024)),
                minimum=1024,
            ),
            default_project=os.getenv("BENBEN_DEFAULT_PROJECT", "实验室公共项目").strip() or "实验室公共项目",
            audit_log_path=audit_log_path,
            audit_max_bytes=_parse_int(
                "BENBEN_AUDIT_MAX_BYTES",
                os.getenv("BENBEN_AUDIT_MAX_BYTES", str(5 * 1024 * 1024)),
                minimum=1024,
            ),
        )


load_dotenv(ROOT_DIR / ".env")


@lru_cache
def get_settings() -> Settings:
    settings = Settings.from_env()
    settings.logs_dir.mkdir(parents=True, exist_ok=True)
    settings.audit_log_path.parent.mkdir(parents=True, exist_ok=True)
    return settings
