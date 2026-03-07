from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# apps/api/src/benusy_api/core/config.py -> parents[5] = Benusy/
_REPO_ROOT = Path(__file__).resolve().parents[5]
_DATA_DIR = _REPO_ROOT / "data"
_LOG_DIR = _REPO_ROOT / "logs"


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
    HOMEPAGE_SITE_NAME: str = "Benusy 品牌合作平台"
    HOMEPAGE_NAV_BRAND: str = "Benusy"
    HOMEPAGE_NAV_FEATURES_LABEL: str = "平台能力"
    HOMEPAGE_NAV_SCENES_LABEL: str = "合作场景"
    HOMEPAGE_NAV_WORKFLOW_LABEL: str = "合作流程"
    HOMEPAGE_NAV_CONTACT_LABEL: str = "联系团队"
    HOMEPAGE_HERO_KICKER: str = "Brand x Creator Collaboration"
    HOMEPAGE_HERO_TITLE: str = "让品牌合作、达人执行和结算复盘在一个后台闭环"
    HOMEPAGE_HERO_SUBTITLE: str = "面向商家、运营和达人团队的内容合作平台，用更轻的流程完成需求发布、任务分配、内容审核、绩效复盘和收益结算。"
    HOMEPAGE_HERO_IMAGE_URL: str = "/static/images/hero-creator-studio.png"
    HOMEPAGE_HERO_PRIMARY_BUTTON_TEXT: str = "申请入驻"
    HOMEPAGE_HERO_PRIMARY_BUTTON_HREF: str = "/auth/register"
    HOMEPAGE_HERO_SECONDARY_BUTTON_TEXT: str = "查看合作流程"
    HOMEPAGE_HERO_SECONDARY_BUTTON_HREF: str = "#how-it-works"
    HOMEPAGE_HERO_PHOTO_PRIMARY_CAPTION: str = "创作者拍摄商品内容，适合放在视觉主位吸引注意力。"
    HOMEPAGE_HERO_PHOTO_SECONDARY_CAPTION: str = "品牌方与运营一起规划活动节奏和素材要求。"
    HOMEPAGE_HERO_PHOTO_TERTIARY_CAPTION: str = "任务数据、审核节点和结算状态放在一个后台面板里。"
    HOMEPAGE_HERO_PROOF_PRIMARY_TITLE: str = "需求统一派发"
    HOMEPAGE_HERO_PROOF_PRIMARY_BODY: str = "商家需求、达人接单和后台审核在一条线上完成，不再反复跳群聊和表格。"
    HOMEPAGE_HERO_PROOF_SECONDARY_TITLE: str = "数据与结算同步"
    HOMEPAGE_HERO_PROOF_SECONDARY_BODY: str = "内容表现、复核节点和收益状态放在同一个工作台里，复盘更快。"
    HOMEPAGE_HERO_TOP_NOTE_LABEL: str = ""
    HOMEPAGE_HERO_TOP_NOTE_TITLE: str = ""
    HOMEPAGE_HERO_BOTTOM_NOTE_LABEL: str = ""
    HOMEPAGE_HERO_BOTTOM_NOTE_TITLE: str = ""
    HOMEPAGE_SHOWCASE_LABEL: str = "平台宣传展示"
    HOMEPAGE_SHOWCASE_TITLE: str = "不同位置放不同照片，每一张都对应一个真实合作场景"
    HOMEPAGE_SHOWCASE_SUBTITLE: str = "主位图负责建立信任，侧位图解释商家协作，下方宽图承接数据和结算逻辑，让访客一眼看懂平台怎么运转。"
    HOMEPAGE_SHOWCASE_PRIMARY_TITLE: str = "拍摄执行场"
    HOMEPAGE_SHOWCASE_PRIMARY_BODY: str = "暖色主图放在首屏主位，负责承接达人、创作者和内容团队的第一感知，也自然连接注册和接单入口。"
    HOMEPAGE_SHOWCASE_SECONDARY_TITLE: str = "商家协作场"
    HOMEPAGE_SHOWCASE_SECONDARY_BODY: str = "青绿色会议场景放在辅助位，强调需求讨论、素材规划和运营陪跑这些更偏后台的能力。"
    HOMEPAGE_SHOWCASE_TERTIARY_TITLE: str = "复盘结算场"
    HOMEPAGE_SHOWCASE_TERTIARY_BODY: str = "横向宽图适合承载数据、审核和收益结果，让结案复盘的价值在首页里就说清楚。"
    HOMEPAGE_CAPABILITIES_LABEL: str = "平台能力"
    HOMEPAGE_CAPABILITIES_TITLE: str = "不是把任务堆给达人，而是把合作真正排成一条线"
    HOMEPAGE_CAPABILITIES_SUBTITLE: str = "Benusy 把品牌需求、达人执行、审核反馈和收益复盘收进同一个协作面板，让每个角色看到自己真正需要的状态。"
    HOMEPAGE_CAPABILITY_HIGHLIGHT_ONE: str = "品牌需求对接"
    HOMEPAGE_CAPABILITY_HIGHLIGHT_TWO: str = "达人执行协同"
    HOMEPAGE_CAPABILITY_HIGHLIGHT_THREE: str = "审核结算闭环"
    HOMEPAGE_CAPABILITY_SPOTLIGHT_LABEL: str = "运营主控台"
    HOMEPAGE_CAPABILITY_SPOTLIGHT_TITLE: str = "从 brief 到结算的全链路视图"
    HOMEPAGE_CAPABILITY_SPOTLIGHT_BODY: str = "首页不是只展示平台长什么样，而是把品牌方最关心的交付节奏、达人最关心的任务状态、运营最关心的复盘节点直接说清楚。"
    HOMEPAGE_CAPABILITY_CARD_ONE_LABEL: str = "商家端"
    HOMEPAGE_CAPABILITY_CARD_ONE_TITLE: str = "需求拆解和投放节奏放在一张面板上"
    HOMEPAGE_CAPABILITY_CARD_ONE_BODY: str = "商家只需要给出目标、预算和内容方向，平台会把 brief、节点和交付要求拆成可执行任务。"
    HOMEPAGE_CAPABILITY_CARD_TWO_LABEL: str = "达人端"
    HOMEPAGE_CAPABILITY_CARD_TWO_TITLE: str = "接单、提交和反馈路径更短"
    HOMEPAGE_CAPABILITY_CARD_TWO_BODY: str = "达人可以直接看到任务要求、参考素材、审核意见和收益状态，不再反复追问运营。"
    HOMEPAGE_CAPABILITY_CARD_THREE_LABEL: str = "运营端"
    HOMEPAGE_CAPABILITY_CARD_THREE_TITLE: str = "审核、催办和复盘可以连续推进"
    HOMEPAGE_CAPABILITY_CARD_THREE_BODY: str = "从分配达人到复核内容，再到跟踪数据和结案，运营不需要再在多个群和表格间切换。"
    HOMEPAGE_WORKFLOW_LABEL: str = "合作流程"
    HOMEPAGE_WORKFLOW_TITLE: str = "商家不用理解复杂系统，也能快速把合作跑起来"
    HOMEPAGE_WORKFLOW_SUBTITLE: str = "Benusy 用更轻的流程承接首次合作和长期运营，两种模式都能走得顺，不会把前台注册当成唯一入口。"
    HOMEPAGE_WORKFLOW_STEP_ONE_TITLE: str = "提交合作目标"
    HOMEPAGE_WORKFLOW_STEP_ONE_BODY: str = "商家告诉我们品类、预期内容方向、发布时间和预算边界，先把合作目的讲清楚。"
    HOMEPAGE_WORKFLOW_STEP_TWO_TITLE: str = "拆解 brief 与达人池"
    HOMEPAGE_WORKFLOW_STEP_TWO_BODY: str = "运营把需求拆成任务模板，筛达人、定节奏、补素材，让执行标准在开始前对齐。"
    HOMEPAGE_WORKFLOW_STEP_THREE_TITLE: str = "审核内容并推进上线"
    HOMEPAGE_WORKFLOW_STEP_THREE_BODY: str = "创作者提交内容后，平台集中处理修改意见、补件和排期，不让沟通碎成很多线程。"
    HOMEPAGE_WORKFLOW_STEP_FOUR_TITLE: str = "复盘数据与收益"
    HOMEPAGE_WORKFLOW_STEP_FOUR_BODY: str = "上线后继续跟踪表现、沉淀结果和收益状态，让下一轮合作有清晰参考。"
    HOMEPAGE_WORKFLOW_SUMMARY_LABEL: str = "交付结果"
    HOMEPAGE_WORKFLOW_SUMMARY_TITLE: str = "对商家来说是一个入口，对运营来说是一张全景图"
    HOMEPAGE_WORKFLOW_SUMMARY_BODY: str = "这套流程既适合临时 campaign，也适合持续达人合作。平台的价值不是多一个系统，而是把零散执行真正收口。"
    HOMEPAGE_MERCHANT_NOTICE_TITLE: str = "商家合作通道"
    HOMEPAGE_MERCHANT_NOTICE_TEXT: str = "商家无需自己摸索平台开户。把需求告诉运营，我们会帮你拆成任务、安排达人、推进审核和复盘。"
    HOMEPAGE_MERCHANT_SERVICE_PUBLISH_TEXT: str = "运营协助整理 brief、发布时间和交付标准"
    HOMEPAGE_MERCHANT_SERVICE_ACCOUNT_TEXT: str = "需要后台视图时，可直接分配商家管理员账号"
    HOMEPAGE_MERCHANT_SERVICE_NO_REGISTER_TEXT: str = "初次合作可先走人工对接，无需前台手动注册"
    HOMEPAGE_MERCHANT_CONTACT_PHONE: str = "400-820-6108"
    HOMEPAGE_MERCHANT_CONTACT_WECHAT: str = "BenusyPartner"
    HOMEPAGE_MERCHANT_CONTACT_EMAIL: str = "brand@benusy.cn"
    HOMEPAGE_CONTACT_SECTION_LABEL: str = "合作入口"
    HOMEPAGE_CONTACT_SECTION_TITLE: str = "联系 Benusy 团队"
    HOMEPAGE_CONTACT_SECTION_SUBTITLE: str = "适合品牌、运营服务商和内容团队的轻协作后台，支持试运营接入和定制流程梳理。"
    HOMEPAGE_CONTACT_INFO_TITLE: str = "合作联系方式"
    HOMEPAGE_CONTACT_FORM_LABEL: str = "在线留言"
    HOMEPAGE_CONTACT_FORM_TITLE: str = "留下你的合作需求"
    HOMEPAGE_CONTACT_FORM_SUBTITLE: str = "如果你希望快速试跑一次 campaign，可以直接写明品类、目标平台、内容方向和预期预算。"
    HOMEPAGE_CONTACT_FORM_BUTTON_TEXT: str = "发送合作信息"
    HOMEPAGE_CONTACT_ADDRESS: str = "上海市徐汇区云锦路 701 号 12F"
    HOMEPAGE_CONTACT_PHONE: str = "021-6012-8819"
    HOMEPAGE_CONTACT_EMAIL: str = "hello@benusy.cn"
    HOMEPAGE_FOOTER_ABOUT_TITLE: str = "关于 Benusy"
    HOMEPAGE_FOOTER_ABOUT_BODY: str = "Benusy 是面向品牌、运营团队和创作者的合作后台，重点解决需求拆解、内容复核和收益复盘三个环节。"
    HOMEPAGE_FOOTER_LINKS_TITLE: str = "快速查看"
    HOMEPAGE_FOOTER_LEGAL_TITLE: str = "平台说明"
    HOMEPAGE_FOOTER_PRIVACY_LABEL: str = "隐私政策"
    HOMEPAGE_FOOTER_TERMS_LABEL: str = "服务条款"
    HOMEPAGE_FOOTER_COOKIE_LABEL: str = "Cookie 说明"
    HOMEPAGE_FOOTER_SUBSCRIBE_TITLE: str = "订阅更新"
    HOMEPAGE_FOOTER_SUBSCRIBE_BODY: str = "留下邮箱，接收新活动模板、合作案例和平台更新。"
    HOMEPAGE_FOOTER_SUBSCRIBE_PLACEHOLDER: str = "输入你的邮箱地址"
    HOMEPAGE_FOOTER_SUBSCRIBE_BUTTON: str = "订阅"
    HOMEPAGE_FOOTER_COPYRIGHT: str = "© 2026 Benusy. All rights reserved."

    # OSS
    ALIYUN_OSS_ENDPOINT: str = ""
    ALIYUN_OSS_ACCESS_KEY_ID: str = ""
    ALIYUN_OSS_ACCESS_KEY_SECRET: str = ""
    ALIYUN_OSS_BUCKET: str = ""
    ALIYUN_OSS_PREFIX: str = ""
    ALIYUN_OSS_PUBLIC_BASE_URL: str = ""
    ALIYUN_OSS_TASK_ATTACHMENT_DIR: str = "task-attachments"
    ALIYUN_OSS_PAYOUT_QR_DIR: str = "payout-qrcodes"

    @field_validator("DATABASE_URL", mode="before")
    @classmethod
    def normalize_database_url(cls, v):
        if not isinstance(v, str) or not v.strip():
            return v
        return _normalize_sqlite_url(v.strip(), app_name="Benusy")

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

    def _normalize_homepage_local_asset(self, value: str, fallback: str) -> str:
        candidate = (value or "").strip()
        if candidate.startswith("/static/"):
            return candidate
        return fallback

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
    def homepage_site_name(self) -> str:
        return self.HOMEPAGE_SITE_NAME

    @property
    def homepage_nav_features_label(self) -> str:
        return self.HOMEPAGE_NAV_FEATURES_LABEL

    @property
    def homepage_nav_scenes_label(self) -> str:
        return self.HOMEPAGE_NAV_SCENES_LABEL

    @property
    def homepage_nav_workflow_label(self) -> str:
        return self.HOMEPAGE_NAV_WORKFLOW_LABEL

    @property
    def homepage_nav_contact_label(self) -> str:
        return self.HOMEPAGE_NAV_CONTACT_LABEL

    @property
    def homepage_hero_kicker(self) -> str:
        return self.HOMEPAGE_HERO_KICKER

    @property
    def homepage_hero_title(self) -> str:
        return self.HOMEPAGE_HERO_TITLE

    @property
    def homepage_hero_subtitle(self) -> str:
        return self.HOMEPAGE_HERO_SUBTITLE

    @property
    def homepage_hero_image_url(self) -> str:
        return self._normalize_homepage_local_asset(
            self.HOMEPAGE_HERO_IMAGE_URL,
            "/static/images/hero-creator-studio.png",
        )

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
    def homepage_hero_photo_primary_caption(self) -> str:
        return self.HOMEPAGE_HERO_PHOTO_PRIMARY_CAPTION

    @property
    def homepage_hero_photo_secondary_caption(self) -> str:
        return self.HOMEPAGE_HERO_PHOTO_SECONDARY_CAPTION

    @property
    def homepage_hero_photo_tertiary_caption(self) -> str:
        return self.HOMEPAGE_HERO_PHOTO_TERTIARY_CAPTION

    @property
    def homepage_hero_proof_primary_title(self) -> str:
        return self.HOMEPAGE_HERO_PROOF_PRIMARY_TITLE

    @property
    def homepage_hero_proof_primary_body(self) -> str:
        return self.HOMEPAGE_HERO_PROOF_PRIMARY_BODY

    @property
    def homepage_hero_proof_secondary_title(self) -> str:
        return self.HOMEPAGE_HERO_PROOF_SECONDARY_TITLE

    @property
    def homepage_hero_proof_secondary_body(self) -> str:
        return self.HOMEPAGE_HERO_PROOF_SECONDARY_BODY

    @property
    def homepage_hero_top_note_label(self) -> str:
        return self.HOMEPAGE_HERO_TOP_NOTE_LABEL

    @property
    def homepage_hero_top_note_title(self) -> str:
        return self.HOMEPAGE_HERO_TOP_NOTE_TITLE

    @property
    def homepage_hero_bottom_note_label(self) -> str:
        return self.HOMEPAGE_HERO_BOTTOM_NOTE_LABEL

    @property
    def homepage_hero_bottom_note_title(self) -> str:
        return self.HOMEPAGE_HERO_BOTTOM_NOTE_TITLE

    @property
    def homepage_showcase_label(self) -> str:
        return self.HOMEPAGE_SHOWCASE_LABEL

    @property
    def homepage_showcase_title(self) -> str:
        return self.HOMEPAGE_SHOWCASE_TITLE

    @property
    def homepage_showcase_subtitle(self) -> str:
        return self.HOMEPAGE_SHOWCASE_SUBTITLE

    @property
    def homepage_showcase_primary_title(self) -> str:
        return self.HOMEPAGE_SHOWCASE_PRIMARY_TITLE

    @property
    def homepage_showcase_primary_body(self) -> str:
        return self.HOMEPAGE_SHOWCASE_PRIMARY_BODY

    @property
    def homepage_showcase_secondary_title(self) -> str:
        return self.HOMEPAGE_SHOWCASE_SECONDARY_TITLE

    @property
    def homepage_showcase_secondary_body(self) -> str:
        return self.HOMEPAGE_SHOWCASE_SECONDARY_BODY

    @property
    def homepage_showcase_tertiary_title(self) -> str:
        return self.HOMEPAGE_SHOWCASE_TERTIARY_TITLE

    @property
    def homepage_showcase_tertiary_body(self) -> str:
        return self.HOMEPAGE_SHOWCASE_TERTIARY_BODY

    @property
    def homepage_capabilities_label(self) -> str:
        return self.HOMEPAGE_CAPABILITIES_LABEL

    @property
    def homepage_capabilities_title(self) -> str:
        return self.HOMEPAGE_CAPABILITIES_TITLE

    @property
    def homepage_capabilities_subtitle(self) -> str:
        return self.HOMEPAGE_CAPABILITIES_SUBTITLE

    @property
    def homepage_capability_highlight_one(self) -> str:
        return self.HOMEPAGE_CAPABILITY_HIGHLIGHT_ONE

    @property
    def homepage_capability_highlight_two(self) -> str:
        return self.HOMEPAGE_CAPABILITY_HIGHLIGHT_TWO

    @property
    def homepage_capability_highlight_three(self) -> str:
        return self.HOMEPAGE_CAPABILITY_HIGHLIGHT_THREE

    @property
    def homepage_capability_spotlight_label(self) -> str:
        return self.HOMEPAGE_CAPABILITY_SPOTLIGHT_LABEL

    @property
    def homepage_capability_spotlight_title(self) -> str:
        return self.HOMEPAGE_CAPABILITY_SPOTLIGHT_TITLE

    @property
    def homepage_capability_spotlight_body(self) -> str:
        return self.HOMEPAGE_CAPABILITY_SPOTLIGHT_BODY

    @property
    def homepage_capability_card_one_label(self) -> str:
        return self.HOMEPAGE_CAPABILITY_CARD_ONE_LABEL

    @property
    def homepage_capability_card_one_title(self) -> str:
        return self.HOMEPAGE_CAPABILITY_CARD_ONE_TITLE

    @property
    def homepage_capability_card_one_body(self) -> str:
        return self.HOMEPAGE_CAPABILITY_CARD_ONE_BODY

    @property
    def homepage_capability_card_two_label(self) -> str:
        return self.HOMEPAGE_CAPABILITY_CARD_TWO_LABEL

    @property
    def homepage_capability_card_two_title(self) -> str:
        return self.HOMEPAGE_CAPABILITY_CARD_TWO_TITLE

    @property
    def homepage_capability_card_two_body(self) -> str:
        return self.HOMEPAGE_CAPABILITY_CARD_TWO_BODY

    @property
    def homepage_capability_card_three_label(self) -> str:
        return self.HOMEPAGE_CAPABILITY_CARD_THREE_LABEL

    @property
    def homepage_capability_card_three_title(self) -> str:
        return self.HOMEPAGE_CAPABILITY_CARD_THREE_TITLE

    @property
    def homepage_capability_card_three_body(self) -> str:
        return self.HOMEPAGE_CAPABILITY_CARD_THREE_BODY

    @property
    def homepage_workflow_label(self) -> str:
        return self.HOMEPAGE_WORKFLOW_LABEL

    @property
    def homepage_workflow_title(self) -> str:
        return self.HOMEPAGE_WORKFLOW_TITLE

    @property
    def homepage_workflow_subtitle(self) -> str:
        return self.HOMEPAGE_WORKFLOW_SUBTITLE

    @property
    def homepage_workflow_step_one_title(self) -> str:
        return self.HOMEPAGE_WORKFLOW_STEP_ONE_TITLE

    @property
    def homepage_workflow_step_one_body(self) -> str:
        return self.HOMEPAGE_WORKFLOW_STEP_ONE_BODY

    @property
    def homepage_workflow_step_two_title(self) -> str:
        return self.HOMEPAGE_WORKFLOW_STEP_TWO_TITLE

    @property
    def homepage_workflow_step_two_body(self) -> str:
        return self.HOMEPAGE_WORKFLOW_STEP_TWO_BODY

    @property
    def homepage_workflow_step_three_title(self) -> str:
        return self.HOMEPAGE_WORKFLOW_STEP_THREE_TITLE

    @property
    def homepage_workflow_step_three_body(self) -> str:
        return self.HOMEPAGE_WORKFLOW_STEP_THREE_BODY

    @property
    def homepage_workflow_step_four_title(self) -> str:
        return self.HOMEPAGE_WORKFLOW_STEP_FOUR_TITLE

    @property
    def homepage_workflow_step_four_body(self) -> str:
        return self.HOMEPAGE_WORKFLOW_STEP_FOUR_BODY

    @property
    def homepage_workflow_summary_label(self) -> str:
        return self.HOMEPAGE_WORKFLOW_SUMMARY_LABEL

    @property
    def homepage_workflow_summary_title(self) -> str:
        return self.HOMEPAGE_WORKFLOW_SUMMARY_TITLE

    @property
    def homepage_workflow_summary_body(self) -> str:
        return self.HOMEPAGE_WORKFLOW_SUMMARY_BODY

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
    def homepage_contact_section_label(self) -> str:
        return self.HOMEPAGE_CONTACT_SECTION_LABEL

    @property
    def homepage_contact_section_subtitle(self) -> str:
        return self.HOMEPAGE_CONTACT_SECTION_SUBTITLE

    @property
    def homepage_contact_info_title(self) -> str:
        return self.HOMEPAGE_CONTACT_INFO_TITLE

    @property
    def homepage_contact_form_label(self) -> str:
        return self.HOMEPAGE_CONTACT_FORM_LABEL

    @property
    def homepage_contact_form_title(self) -> str:
        return self.HOMEPAGE_CONTACT_FORM_TITLE

    @property
    def homepage_contact_form_subtitle(self) -> str:
        return self.HOMEPAGE_CONTACT_FORM_SUBTITLE

    @property
    def homepage_contact_form_button_text(self) -> str:
        return self.HOMEPAGE_CONTACT_FORM_BUTTON_TEXT

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
    def homepage_footer_about_title(self) -> str:
        return self.HOMEPAGE_FOOTER_ABOUT_TITLE

    @property
    def homepage_footer_about_body(self) -> str:
        return self.HOMEPAGE_FOOTER_ABOUT_BODY

    @property
    def homepage_footer_links_title(self) -> str:
        return self.HOMEPAGE_FOOTER_LINKS_TITLE

    @property
    def homepage_footer_legal_title(self) -> str:
        return self.HOMEPAGE_FOOTER_LEGAL_TITLE

    @property
    def homepage_footer_privacy_label(self) -> str:
        return self.HOMEPAGE_FOOTER_PRIVACY_LABEL

    @property
    def homepage_footer_terms_label(self) -> str:
        return self.HOMEPAGE_FOOTER_TERMS_LABEL

    @property
    def homepage_footer_cookie_label(self) -> str:
        return self.HOMEPAGE_FOOTER_COOKIE_LABEL

    @property
    def homepage_footer_subscribe_title(self) -> str:
        return self.HOMEPAGE_FOOTER_SUBSCRIBE_TITLE

    @property
    def homepage_footer_subscribe_body(self) -> str:
        return self.HOMEPAGE_FOOTER_SUBSCRIBE_BODY

    @property
    def homepage_footer_subscribe_placeholder(self) -> str:
        return self.HOMEPAGE_FOOTER_SUBSCRIBE_PLACEHOLDER

    @property
    def homepage_footer_subscribe_button(self) -> str:
        return self.HOMEPAGE_FOOTER_SUBSCRIBE_BUTTON

    @property
    def homepage_footer_copyright(self) -> str:
        return self.HOMEPAGE_FOOTER_COPYRIGHT

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
