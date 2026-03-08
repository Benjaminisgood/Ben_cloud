from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# apps/api/src/benbot_api/core/config.py -> parents[5] = repo root (Benbot/)
_REPO_ROOT = Path(__file__).resolve().parents[5]
_DATA_DIR = _REPO_ROOT / "data"
_WORKSPACE_ROOT = _REPO_ROOT.parent
_STANDARD_REGISTRY_FILE = _WORKSPACE_ROOT / "project_standards" / "registry.yaml"
_LEGACY_REGISTRY_FILE = _WORKSPACE_ROOT / "PROJECT_STANDARDS" / "registry.yaml"

if _STANDARD_REGISTRY_FILE.exists():
    _DEFAULT_REGISTRY_FILE = _STANDARD_REGISTRY_FILE
else:
    _DEFAULT_REGISTRY_FILE = _LEGACY_REGISTRY_FILE


@dataclass
class ProjectConfig:
    id: str
    name: str
    description: str
    icon: str
    port: int           # sub-project port, used for dynamic browser redirect
    internal_url: str   # used for health check (always localhost-based)
    public_url: str     # browser-visible metadata (display/ops), not used for /goto host routing
    color: str = "#3b82f6"
    sso_entry_path: str = "/auth/sso"
    sso_enabled: bool = True


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(_REPO_ROOT / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # App
    APP_NAME: str = "Benbot"
    APP_VERSION: str = "1.0.0"
    APP_ENV: str = "development"
    API_PREFIX: str = "/api"
    HOST: str = "0.0.0.0"
    PORT: int = 80

    # Core
    SECRET_KEY: str = ""
    SSO_SECRET: str = ""
    DATABASE_URL: str = f"sqlite:///{_DATA_DIR / 'benbot.sqlite'}"

    # Session
    REMEMBER_DAYS: int = 30
    SESSION_COOKIE_NAME: str = "benbot_session"
    SESSION_COOKIE_SAMESITE: str = "lax"
    SESSION_COOKIE_SECURE: bool = False

    # Admin bootstrap
    ADMIN_USERNAME: str = ""
    ADMIN_PASSWORD: str = ""
    NANOBOT_API_TOKEN: str = ""
    NANOBOT_API_SCOPES: str = "bug_repair:read,bug_repair:write"
    NANOBOT_API_ALLOWED_IPS: str = "127.0.0.1,::1"

    # Sub-project URLs
    BENOSS_INTERNAL_URL: str = "http://localhost:8000"
    BENOSS_PUBLIC_URL: str = "http://localhost:8000"
    BENLAB_INTERNAL_URL: str = "http://localhost:9000"
    BENLAB_PUBLIC_URL: str = "http://localhost:9000"
    BENUSY_INTERNAL_URL: str = "http://localhost:8100"
    BENUSY_PUBLIC_URL: str = "http://localhost:8100"
    BENOME_INTERNAL_URL: str = "http://localhost:8200"
    BENOME_PUBLIC_URL: str = "http://localhost:8200"
    BENSCI_INTERNAL_URL: str = "http://localhost:8300"
    BENSCI_PUBLIC_URL: str = "http://localhost:8300"
    BENFER_INTERNAL_URL: str = "http://localhost:8400"
    BENFER_PUBLIC_URL: str = "http://localhost:8400"
    BENBEN_INTERNAL_URL: str = "http://localhost:8600"
    BENBEN_PUBLIC_URL: str = "http://localhost:8600"
    BENFAST_INTERNAL_URL: str = "http://localhost:8700"
    BENFAST_PUBLIC_URL: str = "http://localhost:8700"
    BENCRED_INTERNAL_URL: str = "http://localhost:9600"
    BENCRED_PUBLIC_URL: str = "http://localhost:9600"
    BENLINK_INTERNAL_URL: str = "http://localhost:9700"
    BENLINK_PUBLIC_URL: str = "http://localhost:9700"
    BENPREFS_INTERNAL_URL: str = "http://localhost:8800"
    BENPREFS_PUBLIC_URL: str = "http://localhost:8800"
    BENHEALTH_INTERNAL_URL: str = "http://localhost:8900"
    BENHEALTH_PUBLIC_URL: str = "http://localhost:8900"
    BENFINANCE_INTERNAL_URL: str = "http://localhost:9100"
    BENFINANCE_PUBLIC_URL: str = "http://localhost:9100"
    BENSELF_INTERNAL_URL: str = "http://localhost:9800"
    BENSELF_PUBLIC_URL: str = "http://localhost:9800"
    BENJOURNAL_INTERNAL_URL: str = "http://localhost:9200"
    BENJOURNAL_PUBLIC_URL: str = "http://localhost:9200"
    BENPHOTO_INTERNAL_URL: str = "http://localhost:9300"
    BENPHOTO_PUBLIC_URL: str = "http://localhost:9300"
    BENVINYL_INTERNAL_URL: str = "http://localhost:9400"
    BENVINYL_PUBLIC_URL: str = "http://localhost:9400"
    BENREEL_INTERNAL_URL: str = "http://localhost:9500"
    BENREEL_PUBLIC_URL: str = "http://localhost:9500"

    # Health check interval (seconds)
    HEALTH_CHECK_INTERVAL: int = 60
    HEALTH_CHECK_SINGLE_LEADER: bool = True
    ENABLE_PROMETHEUS_METRICS: bool = True

    # Registry consistency check
    PROJECT_REGISTRY_FILE: str = str(_DEFAULT_REGISTRY_FILE)
    PROJECT_REGISTRY_STRICT: bool = False

    # Runtime validation strictness
    SECURITY_STRICT_MODE: bool = False

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

    def get_projects(self) -> list[ProjectConfig]:
        return [
            ProjectConfig(
                id="benoss",
                name="Benoss",
                description="学习小组记录系统 · 文件存档与 AI 摘要",
                icon="📚",
                port=8000,
                internal_url=self.BENOSS_INTERNAL_URL,
                public_url=self.BENOSS_PUBLIC_URL,
                color="#0f4354",
            ),
            ProjectConfig(
                id="benlab",
                name="Benlab",
                description="实验室管理平台 · 成员、活动与物资",
                icon="🔬",
                port=9000,
                internal_url=self.BENLAB_INTERNAL_URL,
                public_url=self.BENLAB_PUBLIC_URL,
                color="#1a3a2a",
            ),
            ProjectConfig(
                id="benusy",
                name="Benusy",
                description="达人运营协作平台 · 任务、审核与结算",
                icon="📈",
                port=8100,
                internal_url=self.BENUSY_INTERNAL_URL,
                public_url=self.BENUSY_PUBLIC_URL,
                color="#5e3b18",
            ),
            ProjectConfig(
                id="benome",
                name="Benome",
                description="ling居家管理平台 · 房源、预订与入住管理",
                icon="🏠",
                port=8200,
                internal_url=self.BENOME_INTERNAL_URL,
                public_url=self.BENOME_PUBLIC_URL,
                color="#0f5a46",
                sso_entry_path="/auth/sso",
                sso_enabled=True,
            ),
            ProjectConfig(
                id="bensci",
                name="Bensci",
                description="CATAPEDIA 文献服务 · 元数据提取与聚合",
                icon="📄",
                port=8300,
                internal_url=self.BENSCI_INTERNAL_URL,
                public_url=self.BENSCI_PUBLIC_URL,
                color="#8b5a9e",
                sso_entry_path="/auth/sso",
                sso_enabled=True,
            ),
            ProjectConfig(
                id="benfer",
                name="Benfer",
                description="剪贴板与文件中转站 · 支持断点续传",
                icon="📋",
                port=8400,
                internal_url=self.BENFER_INTERNAL_URL,
                public_url=self.BENFER_PUBLIC_URL,
                color="#667eea",
                sso_entry_path="/auth/sso",
                sso_enabled=True,
            ),
            ProjectConfig(
                id="benben",
                name="Benben",
                description="Markdown 编辑器 · 在线编辑与预览",
                icon="📝",
                port=8600,
                internal_url=self.BENBEN_INTERNAL_URL,
                public_url=self.BENBEN_PUBLIC_URL,
                color="#e67e22",
                sso_entry_path="/auth/sso",
                sso_enabled=True,
            ),
            ProjectConfig(
                id="benfast",
                name="Benfast",
                description="FastAPI 通用后端模板 · RBAC 与管理能力",
                icon="⚙️",
                port=8700,
                internal_url=self.BENFAST_INTERNAL_URL,
                public_url=self.BENFAST_PUBLIC_URL,
                color="#1f4a8a",
                sso_entry_path="/auth/sso",
                sso_enabled=True,
            ),
            ProjectConfig(
                id="bencred",
                name="Bencred",
                description="凭证保险箱 · 密钥、密码与令牌管理",
                icon="🔐",
                port=9600,
                internal_url=self.BENCRED_INTERNAL_URL,
                public_url=self.BENCRED_PUBLIC_URL,
                color="#4338ca",
                sso_entry_path="/",
                sso_enabled=False,
            ),
            ProjectConfig(
                id="benlink",
                name="Benlink",
                description="链接收藏站 · 保存、整理与追踪网页",
                icon="🔗",
                port=9700,
                internal_url=self.BENLINK_INTERNAL_URL,
                public_url=self.BENLINK_PUBLIC_URL,
                color="#0f766e",
                sso_entry_path="/",
                sso_enabled=False,
            ),
            ProjectConfig(
                id="benprefs",
                name="Benprefs",
                description="偏好档案站 · 喜恶信号、网站习惯与偏好确认板",
                icon="💛",
                port=8800,
                internal_url=self.BENPREFS_INTERNAL_URL,
                public_url=self.BENPREFS_PUBLIC_URL,
                color="#9b3d23",
                sso_entry_path="/auth/sso",
                sso_enabled=True,
            ),
            ProjectConfig(
                id="benhealth",
                name="Benhealth",
                description="健康仪表站 · 运动轨迹、身体指标与健康观察",
                icon="🫀",
                port=8900,
                internal_url=self.BENHEALTH_INTERNAL_URL,
                public_url=self.BENHEALTH_PUBLIC_URL,
                color="#0f6d62",
                sso_entry_path="/auth/sso",
                sso_enabled=True,
            ),
            ProjectConfig(
                id="benfinance",
                name="Benfinance",
                description="财务洞察站 · 账户、流水、预算与资金决策",
                icon="💹",
                port=9100,
                internal_url=self.BENFINANCE_INTERNAL_URL,
                public_url=self.BENFINANCE_PUBLIC_URL,
                color="#183a5a",
                sso_entry_path="/auth/sso",
                sso_enabled=True,
            ),
            ProjectConfig(
                id="benself",
                name="Benself",
                description="数字我闭环站 · raw journal、确认事实与 Graphiti 自我上下文",
                icon="🧠",
                port=9800,
                internal_url=self.BENSELF_INTERNAL_URL,
                public_url=self.BENSELF_PUBLIC_URL,
                color="#0c4f67",
                sso_entry_path="/auth/sso",
                sso_enabled=True,
            ),
            ProjectConfig(
                id="benjournal",
                name="Benjournal",
                description="语音日记站 · 按天录音、合并归档与自动转写",
                icon="🎙️",
                port=9200,
                internal_url=self.BENJOURNAL_INTERNAL_URL,
                public_url=self.BENJOURNAL_PUBLIC_URL,
                color="#6c2f1f",
                sso_entry_path="/auth/sso",
                sso_enabled=True,
            ),
            ProjectConfig(
                id="benphoto",
                name="Benphoto",
                description="照片桌展示站 · OSS 随机拍立得与垃圾桶回收",
                icon="📸",
                port=9300,
                internal_url=self.BENPHOTO_INTERNAL_URL,
                public_url=self.BENPHOTO_PUBLIC_URL,
                color="#cc6a2f",
                sso_entry_path="/auth/sso",
                sso_enabled=True,
            ),
            ProjectConfig(
                id="benvinyl",
                name="Benvinyl",
                description="黑胶音频站 · 每日节目、唱片堆与垃圾桶回收",
                icon="💿",
                port=9400,
                internal_url=self.BENVINYL_INTERNAL_URL,
                public_url=self.BENVINYL_PUBLIC_URL,
                color="#5b3424",
                sso_entry_path="/auth/sso",
                sso_enabled=True,
            ),
            ProjectConfig(
                id="benreel",
                name="Benreel",
                description="老电影放映站 · 每日节目、胶卷切换与垃圾桶回收",
                icon="🎞️",
                port=9500,
                internal_url=self.BENREEL_INTERNAL_URL,
                public_url=self.BENREEL_PUBLIC_URL,
                color="#4a2f23",
                sso_entry_path="/auth/sso",
                sso_enabled=True,
            ),
        ]

    def ensure_data_dirs(self) -> None:
        _DATA_DIR.mkdir(parents=True, exist_ok=True)
        (self.REPO_ROOT / "logs").mkdir(parents=True, exist_ok=True)

    @property
    def nanobot_api_scope_set(self) -> set[str]:
        return {
            scope.strip()
            for scope in self.NANOBOT_API_SCOPES.split(",")
            if scope.strip()
        }

    @property
    def nanobot_allowed_ips_set(self) -> set[str]:
        return {
            item.strip()
            for item in self.NANOBOT_API_ALLOWED_IPS.split(",")
            if item.strip()
        }

    def validate_security(self) -> None:
        insecure_defaults = {
            "dev-secret-key",
            "benbot-sso-secret-2025",
            "nanobot-auto-repair-token-2026",
        }
        missing = []
        if not self.SECRET_KEY.strip():
            missing.append("SECRET_KEY")
        if not self.SSO_SECRET.strip():
            missing.append("SSO_SECRET")
        if not self.NANOBOT_API_TOKEN.strip():
            missing.append("NANOBOT_API_TOKEN")

        if missing:
            raise RuntimeError(
                "Missing required security settings: " + ", ".join(missing)
            )

        weak_fields = []
        if self.SECRET_KEY in insecure_defaults:
            weak_fields.append("SECRET_KEY")
        if self.SSO_SECRET in insecure_defaults:
            weak_fields.append("SSO_SECRET")
        if self.NANOBOT_API_TOKEN in insecure_defaults:
            weak_fields.append("NANOBOT_API_TOKEN")

        if weak_fields:
            raise RuntimeError(
                "Refuse to run with insecure default secrets: "
                + ", ".join(weak_fields)
            )


@lru_cache
def get_settings() -> Settings:
    return Settings()
