from __future__ import annotations

import unittest
from unittest.mock import patch

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from apps.db.models import Article, Base, LLMQueryFilterDropped
from apps.providers.base import ProviderRecord
from apps.services.ingestion_service import ingest_metadata
from apps.services.normalizers import split_semicolon
from apps.services.query_filtering import LLMTokenUsage
from apps.services.query_planner import QueryPlan


class _DummyProvider:
    def __init__(self, records: list[ProviderRecord], *, key: str = "dummy") -> None:
        self.key = key
        self.title = key.title()
        self.description = f"{key} provider"
        self._records = records

    def is_configured(self) -> bool:
        return True

    def search(self, query: str, max_results: int) -> list[ProviderRecord]:
        return list(self._records[:max_results])


class _PassThroughRuntime:
    effective_mode = "none"

    def prepare(self, session: Session, records: list[ProviderRecord], *, logger=None) -> None:
        return None

    def match(self, record: ProviderRecord, *, session: Session | None = None, logger=None) -> tuple[bool, str]:
        return True, "matched"

    def emit_summary(self, *, logger=None) -> None:
        return None

    def persist(self, session: Session, records: list[ProviderRecord], *, logger=None) -> None:
        return None


class _AlwaysDropLLMRuntime:
    effective_mode = "llm"

    def prepare(self, session: Session, records: list[ProviderRecord], *, logger=None) -> None:
        return None

    def match(self, record: ProviderRecord, *, session: Session | None = None, logger=None) -> tuple[bool, str]:
        return False, "query_llm_below_threshold"

    def emit_summary(self, *, logger=None) -> None:
        return None

    def persist(self, session: Session, records: list[ProviderRecord], *, logger=None) -> None:
        return None


class IngestionServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
        Base.metadata.create_all(bind=self.engine)
        self.SessionLocal = sessionmaker(
            bind=self.engine,
            autoflush=False,
            autocommit=False,
            expire_on_commit=False,
            class_=Session,
        )
        self.plan = QueryPlan(
            raw_input="TAP",
            must_terms=[],
            should_terms=[],
            exclude_terms=[],
            phrases=[],
            used_ai=False,
            passthrough_query="TAP",
        )

    def tearDown(self) -> None:
        Base.metadata.drop_all(bind=self.engine)
        self.engine.dispose()

    def test_ingest_does_not_hydrate_missing_keywords_and_abstract(self) -> None:
        provider = _DummyProvider(
            [
                ProviderRecord(
                    doi="10.1000/hydrate",
                    title="TAP kinetics study",
                    source="dummy",
                )
            ]
        )

        with self.SessionLocal() as session:
            with (
                patch("apps.services.ingestion_service.get_all_providers", return_value={"dummy": provider}),
                patch("apps.services.ingestion_service.plan_natural_language_query", return_value=self.plan),
                patch("apps.services.ingestion_service.build_provider_queries", return_value={"dummy": "TAP"}),
            ):
                result = ingest_metadata(
                    session,
                    query="TAP",
                    providers=["dummy"],
                    max_results=20,
                    save_tags=[],
                    query_filter_mode="none",
                )

            article = session.scalar(select(Article).where(Article.doi == "10.1000/hydrate"))

        self.assertIsNotNone(article)
        assert article is not None
        self.assertEqual(result.inserted, 1)
        self.assertEqual(article.abstract, "")
        self.assertEqual(article.journal, "")
        self.assertIsNone(article.citation_count)
        self.assertIsNone(article.impact_factor)
        self.assertEqual(split_semicolon(article.keywords), [])

    def test_ingest_keeps_existing_keywords_and_abstract(self) -> None:
        provider = _DummyProvider(
            [
                ProviderRecord(
                    doi="10.1000/no-hydrate",
                    title="TAP kinetics study",
                    keywords=["TAP"],
                    abstract="Existing abstract.",
                    source="dummy",
                )
            ]
        )

        with self.SessionLocal() as session:
            with (
                patch("apps.services.ingestion_service.get_all_providers", return_value={"dummy": provider}),
                patch("apps.services.ingestion_service.plan_natural_language_query", return_value=self.plan),
                patch("apps.services.ingestion_service.build_provider_queries", return_value={"dummy": "TAP"}),
            ):
                result = ingest_metadata(
                    session,
                    query="TAP",
                    providers=["dummy"],
                    max_results=20,
                    save_tags=[],
                    query_filter_mode="none",
                )

            article = session.scalar(select(Article).where(Article.doi == "10.1000/no-hydrate"))

        self.assertIsNotNone(article)
        assert article is not None
        self.assertEqual(result.inserted, 1)
        self.assertEqual(article.abstract, "Existing abstract.")
        self.assertCountEqual(split_semicolon(article.keywords), ["TAP"])

    def test_ingest_forwards_llm_scoring_prompt_to_query_filter_runtime(self) -> None:
        provider = _DummyProvider(
            [
                ProviderRecord(
                    doi="10.1000/custom-prompt",
                    title="CeO2 catalysis",
                    abstract="TAP reactor study",
                    source="dummy",
                )
            ]
        )
        runtime = _PassThroughRuntime()

        with self.SessionLocal() as session:
            with (
                patch("apps.services.ingestion_service.get_all_providers", return_value={"dummy": provider}),
                patch("apps.services.ingestion_service.plan_natural_language_query", return_value=self.plan),
                patch("apps.services.ingestion_service.build_provider_queries", return_value={"dummy": "TAP"}),
                patch(
                    "apps.services.ingestion_service.build_query_filter_runtime",
                    return_value=runtime,
                ) as mock_build_runtime,
            ):
                ingest_metadata(
                    session,
                    query="TAP",
                    providers=["dummy"],
                    max_results=20,
                    save_tags=[],
                    query_filter_mode="llm",
                    llm_scoring_prompt="是否是催化领域（如果跟TAP实验有关就更好）的论文。",
                )

        self.assertEqual(
            mock_build_runtime.call_args.kwargs["llm_scoring_prompt"],
            "是否是催化领域（如果跟TAP实验有关就更好）的论文。",
        )

    def test_ingest_persists_llm_drop_decision_immediately(self) -> None:
        provider = _DummyProvider(
            [
                ProviderRecord(
                    doi="10.1000/drop-cache",
                    title="General material study",
                    abstract="surface physics",
                    source="dummy",
                )
            ]
        )

        with self.SessionLocal() as session:
            with (
                patch("apps.services.ingestion_service.get_all_providers", return_value={"dummy": provider}),
                patch("apps.services.ingestion_service.plan_natural_language_query", return_value=self.plan),
                patch("apps.services.ingestion_service.build_provider_queries", return_value={"dummy": "TAP"}),
                patch("apps.services.query_filtering._create_openai_client", return_value=object()),
                patch(
                    "apps.services.query_filtering._score_record_with_llm",
                    return_value=(0.05, "不属于目标领域", LLMTokenUsage(9, 3, 12), "qwen-plus"),
                ),
            ):
                result = ingest_metadata(
                    session,
                    query="TAP",
                    providers=["dummy"],
                    max_results=20,
                    save_tags=[],
                    query_filter_mode="llm",
                    llm_scoring_prompt="是否是催化领域（如果跟TAP实验有关就更好）的论文。",
                )

            drop_row = session.scalar(select(LLMQueryFilterDropped).where(LLMQueryFilterDropped.doi == "10.1000/drop-cache"))

        self.assertEqual(result.inserted, 0)
        self.assertEqual(result.updated, 0)
        self.assertIsNotNone(drop_row)
        assert drop_row is not None
        self.assertEqual(drop_row.reason, "不属于目标领域")
        self.assertEqual(drop_row.total_tokens, 12)

    def test_llm_mode_can_skip_rereview_for_existing_articles(self) -> None:
        provider = _DummyProvider(
            [
                ProviderRecord(
                    doi="10.1000/existing-keep",
                    title="Updated title",
                    source="dummy",
                )
            ]
        )
        runtime = _AlwaysDropLLMRuntime()

        with self.SessionLocal() as session:
            session.add(
                Article(
                    doi="10.1000/existing-keep",
                    title="Old title",
                    source="seed",
                )
            )
            session.commit()

            with (
                patch("apps.services.ingestion_service.get_all_providers", return_value={"dummy": provider}),
                patch("apps.services.ingestion_service.plan_natural_language_query", return_value=self.plan),
                patch("apps.services.ingestion_service.build_provider_queries", return_value={"dummy": "TAP"}),
                patch("apps.services.ingestion_service.build_query_filter_runtime", return_value=runtime),
            ):
                result = ingest_metadata(
                    session,
                    query="TAP",
                    providers=["dummy"],
                    max_results=20,
                    save_tags=[],
                    query_filter_mode="llm",
                    llm_review_existing_articles=False,
                )

            article = session.scalar(select(Article).where(Article.doi == "10.1000/existing-keep"))

        self.assertIsNotNone(article)
        assert article is not None
        self.assertEqual(result.inserted, 0)
        self.assertEqual(result.updated, 1)
        self.assertEqual(article.title, "Updated title")

    def test_min_impact_factor_only_uses_article_field(self) -> None:
        provider = _DummyProvider(
            [
                ProviderRecord(
                    doi="10.1000/no-article-impact",
                    title="TAP kinetics study",
                    journal="Journal of Catalysis",
                    source="dummy",
                )
            ]
        )

        with self.SessionLocal() as session:
            with (
                patch("apps.services.ingestion_service.get_all_providers", return_value={"dummy": provider}),
                patch("apps.services.ingestion_service.plan_natural_language_query", return_value=self.plan),
                patch("apps.services.ingestion_service.build_provider_queries", return_value={"dummy": "TAP"}),
                patch("apps.services.ingestion_service.lookup_impact_factor", return_value=99.0, create=True),
                patch(
                    "apps.services.ingestion_service.load_journal_impact_factors",
                    return_value={"journal of catalysis": 99.0},
                    create=True,
                ),
            ):
                result = ingest_metadata(
                    session,
                    query="TAP",
                    providers=["dummy"],
                    max_results=20,
                    save_tags=[],
                    query_filter_mode="none",
                    min_impact_factor=10.0,
                )

            article = session.scalar(select(Article).where(Article.doi == "10.1000/no-article-impact"))

        self.assertIsNone(article)
        self.assertEqual(result.inserted, 0)
        self.assertEqual(result.updated, 0)
        self.assertEqual(result.skipped, 0)
        self.assertEqual(result.merged_unique, 1)

    def test_runtime_added_provider_is_executed(self) -> None:
        primary_provider = _DummyProvider(
            [
                ProviderRecord(
                    doi="10.1000/runtime-dummy",
                    title="Primary provider result",
                    source="dummy",
                )
            ],
            key="dummy",
        )
        runtime_added_provider = _DummyProvider(
            [
                ProviderRecord(
                    doi="10.1000/runtime-extra",
                    title="Runtime provider result",
                    source="extra",
                )
            ],
            key="extra",
        )
        provider_list_calls = {"count": 0}

        def provider_keys_provider() -> list[str]:
            provider_list_calls["count"] += 1
            if provider_list_calls["count"] == 1:
                return ["dummy"]
            return ["dummy", "extra"]

        def build_queries(_: QueryPlan, provider_keys: list[str], context_texts=None) -> dict[str, str]:
            del context_texts
            return {key: "TAP" for key in provider_keys}

        with self.SessionLocal() as session:
            with (
                patch(
                    "apps.services.ingestion_service.get_all_providers",
                    return_value={"dummy": primary_provider, "extra": runtime_added_provider},
                ),
                patch("apps.services.ingestion_service.plan_natural_language_query", return_value=self.plan),
                patch("apps.services.ingestion_service.build_provider_queries", side_effect=build_queries),
            ):
                result = ingest_metadata(
                    session,
                    query="TAP",
                    providers=["dummy"],
                    max_results=20,
                    save_tags=[],
                    query_filter_mode="none",
                    provider_keys_provider=provider_keys_provider,
                )

            primary_article = session.scalar(select(Article).where(Article.doi == "10.1000/runtime-dummy"))
            runtime_article = session.scalar(select(Article).where(Article.doi == "10.1000/runtime-extra"))

        self.assertIsNotNone(primary_article)
        self.assertIsNotNone(runtime_article)
        self.assertEqual(result.inserted, 2)
        stats_by_provider = {item.provider: item for item in result.provider_stats}
        self.assertIn("dummy", stats_by_provider)
        self.assertIn("extra", stats_by_provider)
        self.assertEqual(stats_by_provider["dummy"].fetched, 1)
        self.assertEqual(stats_by_provider["extra"].fetched, 1)


if __name__ == "__main__":
    unittest.main()
