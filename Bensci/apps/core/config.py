from __future__ import annotations

from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


def _split_csv(value: str | list[str] | tuple[str, ...]) -> list[str]:
    if isinstance(value, str):
        return [item.strip() for item in value.split(",") if item.strip()]
    if isinstance(value, (list, tuple)):
        return [str(item).strip() for item in value if str(item).strip()]
    return []
PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "data"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=PROJECT_ROOT / ".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "CATAPEDIA Metadata Service"
    app_version: str = "0.1.0"
    api_prefix: str = "/api"

    base_dir: Path = DATA_DIR
    sqlite_filename: str = "metadata.db"
    sqlite_journal_mode: str = "WAL"
    sqlite_busy_timeout_seconds: float = 30.0
    sqlite_synchronous: str = "NORMAL"

    request_timeout_seconds: int = 60
    request_user_agent: str = "catapedia-metadata/0.1"
    provider_sleep_seconds: float = 0.2
    journal_metrics_csv_path: Path | None = PROJECT_ROOT / "data" / "journal_impact_factors.csv"
    enrichment_workers: int = 4
    task_worker_concurrency: int = 2
    task_poll_interval_seconds: float = 0.5
    export_dir: Path = DATA_DIR / "exports"
    auto_enrichment_enabled: bool = True
    auto_enrichment_interval_seconds: int = 180
    auto_enrichment_limit: int = 100
    auto_enrichment_workers: int = 4

    aliyun_ai_api_key: str | None = None
    aliyun_ai_api_base_url: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    aliyun_ai_model: str = "qwen-plus"
    aliyun_ai_embedding_model: str = "text-embedding-v4"
    aliyun_ai_embedding_dimensions: int = 1024
    query_filter_llm_fallback_models_raw: str = Field(default="", validation_alias="query_filter_llm_fallback_models")

    default_query: str = (
        '(("temporal analysis of products" OR TAP) AND (catalysis OR catalytic)) '
        'OR ((catalysis OR microkinetic OR kinetics) AND (energy OR CO2 OR hydrogen OR methane OR ammonia))'
    )

    default_providers_raw: str = Field(
        default="crossref,openalex,pubmed,springer,elsevier,arxiv",
        validation_alias="default_providers",
    )

    springer_meta_api_key: str | None = None
    springer_meta_api_base: str = "https://api.springernature.com/meta/v2/json"

    elsevier_api_key: str | None = None

    cors_origins_raw: str = Field(default="*", validation_alias="cors_origins")
    sso_secret: str = "benbot-sso-secret-2025"

    @property
    def resolved_base_dir(self) -> Path:
        base_dir = self.base_dir
        if not base_dir.is_absolute():
            base_dir = PROJECT_ROOT / base_dir
        return base_dir.resolve()

    @property
    def database_url(self) -> str:
        db_path = self.resolved_base_dir / self.sqlite_filename
        db_path.parent.mkdir(parents=True, exist_ok=True)
        return f"sqlite:///{db_path}"

    @property
    def query_filter_llm_fallback_models(self) -> list[str]:
        return _split_csv(self.query_filter_llm_fallback_models_raw)

    @query_filter_llm_fallback_models.setter
    def query_filter_llm_fallback_models(self, value: str | list[str] | tuple[str, ...]) -> None:
        object.__setattr__(self, "query_filter_llm_fallback_models_raw", ",".join(_split_csv(value)))

    @query_filter_llm_fallback_models.deleter
    def query_filter_llm_fallback_models(self) -> None:
        object.__setattr__(self, "query_filter_llm_fallback_models_raw", "")

    @property
    def default_providers(self) -> list[str]:
        return _split_csv(self.default_providers_raw)

    @default_providers.setter
    def default_providers(self, value: str | list[str] | tuple[str, ...]) -> None:
        object.__setattr__(self, "default_providers_raw", ",".join(_split_csv(value)))

    @default_providers.deleter
    def default_providers(self) -> None:
        object.__setattr__(self, "default_providers_raw", "")

    @property
    def cors_origins(self) -> list[str]:
        return _split_csv(self.cors_origins_raw)

    @cors_origins.setter
    def cors_origins(self, value: str | list[str] | tuple[str, ...]) -> None:
        object.__setattr__(self, "cors_origins_raw", ",".join(_split_csv(value)))

    @cors_origins.deleter
    def cors_origins(self) -> None:
        object.__setattr__(self, "cors_origins_raw", "")


settings = Settings()
