from apps.core.config import Settings


def test_settings_parses_csv_env_values() -> None:
    settings = Settings(
        default_providers="crossref, openalex , pubmed",
        cors_origins="https://a.test, https://b.test",
        query_filter_llm_fallback_models="qwen-plus, qwen-turbo",
    )

    assert settings.default_providers == ["crossref", "openalex", "pubmed"]
    assert settings.cors_origins == ["https://a.test", "https://b.test"]
    assert settings.query_filter_llm_fallback_models == ["qwen-plus", "qwen-turbo"]
