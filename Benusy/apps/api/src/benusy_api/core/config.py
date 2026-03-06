from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# apps/api/src/benusy_api/core/config.py -> parents[5] = Benusy/
_REPO_ROOT = Path(__file__).resolve().parents[5]
_DATA_DIR = _REPO_ROOT / "data"
_LOG_DIR = _REPO_ROOT / "logs"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(_REPO_ROOT / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # App
    APP_NAME: str = "Influencer Promotion Platform"
    APP_VERSION: str = "1.0.0"
    APP_ENV: str = "development"
    DEBUG: bool = True
    API_PREFIX: str = "/api/v1"
    HOST: str = "0.0.0.0"
    PORT: int = 8100

    # Core / auth
    SECRET_KEY: str = "development-secret-key"
    SSO_SECRET: str = "benbot-sso-secret-2025"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REMEMBER_ME_ACCESS_TOKEN_EXPIRE_DAYS: int = 30
    DATABASE_URL: str = f"sqlite:///{_DATA_DIR / 'benusy.sqlite'}"
    DB_BOOTSTRAP_CREATE_ALL: bool = False

    # Session
    REMEMBER_DAYS: int = 30
    SESSION_COOKIE_NAME: str = "benusy_session"
    SESSION_COOKIE_SAMESITE: str = "lax"
    SESSION_COOKIE_SECURE: bool = False

    # Runtime options
    METRICS_UPDATE_INTERVAL_SECONDS: int = 1800
    DEFAULT_USER_WEIGHT: float = 0.001

    # Homepage content
    HOMEPAGE_NAV_BRAND: str = "Influencer Platform"
    HOMEPAGE_HERO_TITLE: str = "影响者推广平台"
    HOMEPAGE_HERO_SUBTITLE: str = "连接品牌与优质影响者，实现高效、精准的营销推广"
    HOMEPAGE_HERO_IMAGE_URL: str = "/static/images/hero-image.png"
    HOMEPAGE_HERO_PRIMARY_BUTTON_TEXT: str = "立即注册"
    HOMEPAGE_HERO_PRIMARY_BUTTON_HREF: str = "/auth/register"
    HOMEPAGE_HERO_SECONDARY_BUTTON_TEXT: str = "了解更多"
    HOMEPAGE_HERO_SECONDARY_BUTTON_HREF: str = "#how-it-works"
    HOMEPAGE_MERCHANT_NOTICE_TITLE: str = "商家合作通道"
    HOMEPAGE_MERCHANT_NOTICE_TEXT: str = "商家请直接联系站长，由站长协助发布需求或开通商家管理员账号，商家无需手动注册。"
    HOMEPAGE_MERCHANT_SERVICE_PUBLISH_TEXT: str = "站长协助商家发布需求并跟进上线流程"
    HOMEPAGE_MERCHANT_SERVICE_ACCOUNT_TEXT: str = "站长可直接分配商家管理员账号用于后台管理"
    HOMEPAGE_MERCHANT_SERVICE_NO_REGISTER_TEXT: str = "商家不需要在前台手动注册"
    HOMEPAGE_MERCHANT_CONTACT_PHONE: str = ""
    HOMEPAGE_MERCHANT_CONTACT_WECHAT: str = ""
    HOMEPAGE_MERCHANT_CONTACT_EMAIL: str = ""
    HOMEPAGE_CONTACT_SECTION_TITLE: str = "联系我们"
    HOMEPAGE_CONTACT_SECTION_SUBTITLE: str = "如果您有任何问题或建议，欢迎随时联系我们"
    HOMEPAGE_CONTACT_ADDRESS: str = ""
    HOMEPAGE_CONTACT_PHONE: str = ""
    HOMEPAGE_CONTACT_EMAIL: str = ""

    # OSS
    ALIYUN_OSS_ENDPOINT: str = ""
    ALIYUN_OSS_ACCESS_KEY_ID: str = ""
    ALIYUN_OSS_ACCESS_KEY_SECRET: str = ""
    ALIYUN_OSS_BUCKET: str = ""
    ALIYUN_OSS_PREFIX: str = ""
    ALIYUN_OSS_PUBLIC_BASE_URL: str = ""
    ALIYUN_OSS_TASK_ATTACHMENT_DIR: str = "task-attachments"
    ALIYUN_OSS_PAYOUT_QR_DIR: str = "payout-qrcodes"

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

    def oss_enabled(self) -> bool:
        return all(
            [
                self.ALIYUN_OSS_ENDPOINT,
                self.ALIYUN_OSS_ACCESS_KEY_ID,
                self.ALIYUN_OSS_ACCESS_KEY_SECRET,
                self.ALIYUN_OSS_BUCKET,
            ]
        )

    # Backward-compatible aliases for legacy modules.
    @property
    def app_name(self) -> str:
        return self.APP_NAME

    @property
    def environment(self) -> str:
        return self.APP_ENV

    @property
    def debug(self) -> bool:
        return self.DEBUG

    @property
    def api_v1_prefix(self) -> str:
        return self.API_PREFIX

    @property
    def secret_key(self) -> str:
        return self.SECRET_KEY

    @property
    def access_token_expire_minutes(self) -> int:
        return self.ACCESS_TOKEN_EXPIRE_MINUTES

    @property
    def remember_me_access_token_expire_days(self) -> int:
        return self.REMEMBER_ME_ACCESS_TOKEN_EXPIRE_DAYS

    @property
    def algorithm(self) -> str:
        return self.ALGORITHM

    @property
    def database_url(self) -> str:
        return self.DATABASE_URL

    @property
    def metrics_update_interval_seconds(self) -> int:
        return self.METRICS_UPDATE_INTERVAL_SECONDS

    @property
    def default_user_weight(self) -> float:
        return self.DEFAULT_USER_WEIGHT

    @property
    def homepage_nav_brand(self) -> str:
        return self.HOMEPAGE_NAV_BRAND

    @property
    def homepage_hero_title(self) -> str:
        return self.HOMEPAGE_HERO_TITLE

    @property
    def homepage_hero_subtitle(self) -> str:
        return self.HOMEPAGE_HERO_SUBTITLE

    @property
    def homepage_hero_image_url(self) -> str:
        return self.HOMEPAGE_HERO_IMAGE_URL

    @property
    def homepage_hero_primary_button_text(self) -> str:
        return self.HOMEPAGE_HERO_PRIMARY_BUTTON_TEXT

    @property
    def homepage_hero_primary_button_href(self) -> str:
        return self.HOMEPAGE_HERO_PRIMARY_BUTTON_HREF

    @property
    def homepage_hero_secondary_button_text(self) -> str:
        return self.HOMEPAGE_HERO_SECONDARY_BUTTON_TEXT

    @property
    def homepage_hero_secondary_button_href(self) -> str:
        return self.HOMEPAGE_HERO_SECONDARY_BUTTON_HREF

    @property
    def homepage_merchant_notice_title(self) -> str:
        return self.HOMEPAGE_MERCHANT_NOTICE_TITLE

    @property
    def homepage_merchant_notice_text(self) -> str:
        return self.HOMEPAGE_MERCHANT_NOTICE_TEXT

    @property
    def homepage_merchant_service_publish_text(self) -> str:
        return self.HOMEPAGE_MERCHANT_SERVICE_PUBLISH_TEXT

    @property
    def homepage_merchant_service_account_text(self) -> str:
        return self.HOMEPAGE_MERCHANT_SERVICE_ACCOUNT_TEXT

    @property
    def homepage_merchant_service_no_register_text(self) -> str:
        return self.HOMEPAGE_MERCHANT_SERVICE_NO_REGISTER_TEXT

    @property
    def homepage_merchant_contact_phone(self) -> str:
        return self.HOMEPAGE_MERCHANT_CONTACT_PHONE

    @property
    def homepage_merchant_contact_wechat(self) -> str:
        return self.HOMEPAGE_MERCHANT_CONTACT_WECHAT

    @property
    def homepage_merchant_contact_email(self) -> str:
        return self.HOMEPAGE_MERCHANT_CONTACT_EMAIL

    @property
    def homepage_contact_section_title(self) -> str:
        return self.HOMEPAGE_CONTACT_SECTION_TITLE

    @property
    def homepage_contact_section_subtitle(self) -> str:
        return self.HOMEPAGE_CONTACT_SECTION_SUBTITLE

    @property
    def homepage_contact_address(self) -> str:
        return self.HOMEPAGE_CONTACT_ADDRESS

    @property
    def homepage_contact_phone(self) -> str:
        return self.HOMEPAGE_CONTACT_PHONE

    @property
    def homepage_contact_email(self) -> str:
        return self.HOMEPAGE_CONTACT_EMAIL

    @property
    def aliyun_oss_endpoint(self) -> str:
        return self.ALIYUN_OSS_ENDPOINT

    @property
    def aliyun_oss_access_key_id(self) -> str:
        return self.ALIYUN_OSS_ACCESS_KEY_ID

    @property
    def aliyun_oss_access_key_secret(self) -> str:
        return self.ALIYUN_OSS_ACCESS_KEY_SECRET

    @property
    def aliyun_oss_bucket(self) -> str:
        return self.ALIYUN_OSS_BUCKET

    @property
    def aliyun_oss_prefix(self) -> str:
        return self.ALIYUN_OSS_PREFIX

    @property
    def aliyun_oss_public_base_url(self) -> str:
        return self.ALIYUN_OSS_PUBLIC_BASE_URL

    @property
    def aliyun_oss_task_attachment_dir(self) -> str:
        return self.ALIYUN_OSS_TASK_ATTACHMENT_DIR

    @property
    def aliyun_oss_payout_qr_dir(self) -> str:
        return self.ALIYUN_OSS_PAYOUT_QR_DIR


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
