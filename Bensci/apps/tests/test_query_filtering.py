from __future__ import annotations

import unittest
from unittest.mock import patch

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from apps.core.config import settings
from apps.db.models import Article, Base, LLMQueryFilterDropped
from apps.providers import ProviderRecord
from apps.services.query_filtering import _build_llm_scoring_payload
from apps.services.query_filtering import LLMTokenUsage
from apps.services.query_filtering import build_query_filter_runtime
from apps.services.query_filtering import _pack_embedding
from apps.services.query_planner import QueryPlan, build_query_embedding_text


def _record(**kwargs: str) -> ProviderRecord:
    return ProviderRecord(
        doi=kwargs.get("doi", "10.1000/test"),
        title=kwargs.get("title", ""),
        abstract=kwargs.get("abstract", ""),
        keywords=kwargs.get("keywords", "").split(",") if kwargs.get("keywords") else [],
        journal=kwargs.get("journal", ""),
        publisher=kwargs.get("publisher", ""),
        corresponding_author=kwargs.get("corresponding_author", ""),
        affiliations=kwargs.get("affiliations", "").split(",") if kwargs.get("affiliations") else [],
        source=kwargs.get("source", ""),
        published_date=kwargs.get("published_date", ""),
    )


class QueryFilteringRuntimeTests(unittest.TestCase):
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

    def tearDown(self) -> None:
        Base.metadata.drop_all(bind=self.engine)
        self.engine.dispose()

    def test_none_mode_passes_record(self) -> None:
        plan = QueryPlan(
            raw_input="TAP",
            must_terms=[],
            should_terms=[],
            exclude_terms=[],
            phrases=[],
            used_ai=False,
            passthrough_query="TAP",
        )
        runtime = build_query_filter_runtime(mode="none", threshold=0.35, raw_query="TAP", plan=plan)

        matched, reason = runtime.match(_record(title="irrelevant paper"))

        self.assertTrue(matched)
        self.assertEqual(reason, "matched")

    def test_boolean_mode_uses_query_boolean_filter(self) -> None:
        query = '("temporal analysis of products" OR TAP) AND ("Au/SBA-15")'
        plan = QueryPlan(
            raw_input=query,
            must_terms=[],
            should_terms=[],
            exclude_terms=[],
            phrases=[],
            used_ai=False,
            passthrough_query=query,
        )
        runtime = build_query_filter_runtime(mode="boolean", threshold=0.35, raw_query=query, plan=plan)

        matched_ok, _ = runtime.match(_record(doi="10.1000/ok", title="TAP study", abstract="Au/SBA-15 catalyst"))
        matched_bad, reason_bad = runtime.match(_record(doi="10.1000/bad", title="TAP study", abstract="gold catalyst"))

        self.assertTrue(matched_ok)
        self.assertFalse(matched_bad)
        self.assertEqual(reason_bad, "query_boolean_filter_not_matched")

    def test_embedding_mode_reuses_cached_vector_for_same_effective_text(self) -> None:
        plan = QueryPlan(
            raw_input="帮我找 TAP 和 microkinetic 相关文献",
            must_terms=[],
            should_terms=[],
            exclude_terms=[],
            phrases=[],
            used_ai=False,
            passthrough_query="帮我找 TAP 和 microkinetic 相关文献",
        )
        record = _record(
            doi="10.1000/embed",
            title="TAP kinetics study",
            abstract="microkinetic model for TAP reactor",
            keywords="TAP,microkinetic",
        )

        with self.SessionLocal() as session:
            article = Article(
                doi="10.1000/embed",
                title=record.title,
                abstract=record.abstract,
                keywords="TAP; microkinetic",
                embedding_vector=_pack_embedding([0.5, 0.5, 0.5]),
                embedding_model="test-embedding",
                embedding_dimensions=3,
                embedding_text_hash="",
            )
            session.add(article)
            session.flush()

            from apps.services.query_filtering import _hash_text, _merged_record_text

            article.embedding_text_hash = _hash_text(_merged_record_text(article, record))
            session.commit()

            with patch.object(settings, "aliyun_ai_embedding_model", "test-embedding"):
                with patch.object(settings, "aliyun_ai_embedding_dimensions", 3):
                    with patch("apps.services.query_filtering._create_openai_client", return_value=object()):
                        with patch(
                            "apps.services.query_filtering._embedding_vectors",
                            return_value=[[1.0, 0.0, 0.0]],
                        ) as mock_embed:
                            runtime = build_query_filter_runtime(
                                mode="embedding",
                                threshold=0.42,
                                raw_query=plan.raw_input,
                                plan=plan,
                            )
                            runtime.prepare(session, [record])

        self.assertEqual(runtime.effective_mode, "embedding")
        self.assertEqual(mock_embed.call_count, 1)
        self.assertIn("10.1000/embed", runtime.embedding_scores)
        self.assertAlmostEqual(runtime.embedding_scores["10.1000/embed"], 0.577350269, places=6)

    def test_embedding_mode_hard_filters_must_terms_before_similarity(self) -> None:
        plan = QueryPlan(
            raw_input="查找 TAP 相关文献",
            must_terms=["TAP"],
            should_terms=["microkinetic"],
            exclude_terms=[],
            phrases=[],
            used_ai=True,
            passthrough_query=None,
        )
        missing_record = _record(doi="10.1000/miss", title="VOC oxidation study", abstract="gold catalyst")
        matched_record = _record(doi="10.1000/hit", title="TAP kinetics study", abstract="microkinetic reactor")

        with self.SessionLocal() as session:
            with patch("apps.services.query_filtering._create_openai_client", return_value=object()):
                with patch(
                    "apps.services.query_filtering._embedding_vectors",
                    side_effect=[
                        [[1.0, 0.0, 0.0]],
                        [[1.0, 0.0, 0.0]],
                    ],
                ) as mock_embed:
                    runtime = build_query_filter_runtime(
                        mode="embedding",
                        threshold=0.50,
                        raw_query=plan.raw_input,
                        plan=plan,
                    )
                    runtime.prepare(session, [missing_record, matched_record])

        self.assertEqual(mock_embed.call_count, 2)
        self.assertEqual(len(mock_embed.call_args_list[1].kwargs["texts"]), 1)
        self.assertEqual(runtime.embedding_score_sources["10.1000/miss"], "must_terms")
        self.assertEqual(runtime.embedding_precheck_failures["10.1000/miss"], ["tap"])

        matched_missing, reason_missing = runtime.match(missing_record)
        matched_hit, reason_hit = runtime.match(matched_record)

        self.assertFalse(matched_missing)
        self.assertEqual(reason_missing, "query_embedding_must_terms_not_matched")
        self.assertTrue(matched_hit)
        self.assertEqual(reason_hit, "matched")

    def test_embedding_mode_emits_missing_must_terms_summary(self) -> None:
        plan = QueryPlan(
            raw_input="查找 TAP 和 Au/SBA-15 相关文献",
            must_terms=["TAP", "Au/SBA-15"],
            should_terms=[],
            exclude_terms=[],
            phrases=[],
            used_ai=True,
            passthrough_query=None,
        )
        records = [
            _record(doi="10.1000/m1", title="VOC oxidation study", abstract="gold catalyst"),
            _record(doi="10.1000/m2", title="TAP kinetics study", abstract="zeolite catalyst"),
        ]
        logs: list[str] = []

        with self.SessionLocal() as session:
            with patch("apps.services.query_filtering._create_openai_client", return_value=object()):
                with patch(
                    "apps.services.query_filtering._embedding_vectors",
                    return_value=[[1.0, 0.0, 0.0]],
                ):
                    runtime = build_query_filter_runtime(
                        mode="embedding",
                        threshold=0.50,
                        raw_query=plan.raw_input,
                        plan=plan,
                    )
                    runtime.prepare(session, records, logger=logs.append)
                    for record in records:
                        runtime.match(record, logger=logs.append)
                    runtime.emit_summary(logger=logs.append)

        summary_line = next(
            (line for line in logs if "must_terms 缺失词统计" in line),
            "",
        )
        self.assertIn("tap=1", summary_line)
        self.assertIn("au/sba-15=2", summary_line)

    def test_llm_mode_uses_score_threshold(self) -> None:
        plan = QueryPlan(
            raw_input="TAP microkinetic",
            must_terms=["microkinetic"],
            should_terms=["TAP"],
            exclude_terms=[],
            phrases=[],
            used_ai=True,
            passthrough_query=None,
        )
        record = _record(doi="10.1000/llm", title="TAP kinetics study", abstract="microkinetic model")

        with patch("apps.services.query_filtering._create_openai_client", return_value=object()):
            with patch(
                "apps.services.query_filtering._score_record_with_llm",
                return_value=(0.62, "主题基本匹配", LLMTokenUsage(10, 4, 14), "qwen-plus"),
            ):
                runtime = build_query_filter_runtime(
                    mode="llm",
                    threshold=0.60,
                    raw_query="TAP microkinetic",
                    plan=plan,
                )
                matched, reason = runtime.match(record)

        self.assertTrue(matched)
        self.assertEqual(reason, "matched")
        self.assertAlmostEqual(runtime.llm_scores["10.1000/llm"], 0.62, places=6)
        self.assertEqual(runtime.llm_total_tokens_total, 14)

    def test_llm_mode_rejects_when_score_below_threshold(self) -> None:
        plan = QueryPlan(
            raw_input="TAP microkinetic",
            must_terms=["microkinetic"],
            should_terms=["TAP"],
            exclude_terms=[],
            phrases=[],
            used_ai=True,
            passthrough_query=None,
        )
        record = _record(doi="10.1000/llm-low", title="General catalysis study", abstract="surface reaction")

        with patch("apps.services.query_filtering._create_openai_client", return_value=object()):
            with patch(
                "apps.services.query_filtering._score_record_with_llm",
                return_value=(0.24, "只有弱相关", LLMTokenUsage(8, 4, 12), "qwen-plus"),
            ):
                runtime = build_query_filter_runtime(
                    mode="llm",
                    threshold=0.60,
                    raw_query="TAP microkinetic",
                    plan=plan,
                )
                matched, reason = runtime.match(record)

        self.assertFalse(matched)
        self.assertEqual(reason, "query_llm_below_threshold")

    def test_llm_mode_accepts_custom_review_prompt_and_uses_query_relevance(self) -> None:
        plan = QueryPlan(
            raw_input="CeO2",
            must_terms=[],
            should_terms=[],
            exclude_terms=[],
            phrases=[],
            used_ai=False,
            passthrough_query="CeO2",
        )
        record = _record(doi="10.1000/custom-llm", title="CeO2 catalysis", abstract="TAP reactor study")

        with patch("apps.services.query_filtering._create_openai_client", return_value=object()):
            with patch(
                "apps.services.query_filtering._score_record_with_llm",
                return_value=(0.88, "符合自定义标准", LLMTokenUsage(9, 3, 12), "qwen-plus"),
            ) as mock_score:
                runtime = build_query_filter_runtime(
                    mode="llm",
                    threshold=0.60,
                    raw_query="CeO2",
                    plan=plan,
                    llm_scoring_prompt="是否是催化领域（如果跟TAP实验有关就更好）的论文。",
                )
                matched, reason = runtime.match(record)

        self.assertTrue(matched)
        self.assertEqual(reason, "matched")
        self.assertEqual(
            mock_score.call_args.kwargs["llm_scoring_prompt"],
            "是否是催化领域（如果跟TAP实验有关就更好）的论文。",
        )
        self.assertEqual(mock_score.call_args.kwargs["model_name"], runtime.llm_model_candidates[0])
        self.assertIn('"kind": "query_relevance"', runtime.llm_decision_scope_text)
        self.assertIn('"review_constraints"', runtime.llm_decision_scope_text)

    def test_llm_mode_uses_sqlite_drop_cache_before_scoring(self) -> None:
        plan = QueryPlan(
            raw_input="CeO2",
            must_terms=[],
            should_terms=[],
            exclude_terms=[],
            phrases=[],
            used_ai=False,
            passthrough_query="CeO2",
        )
        record = _record(doi="10.1000/cached-drop", title="CeO2 materials", abstract="surface study")
        logs: list[str] = []

        with self.SessionLocal() as session:
            with patch("apps.services.query_filtering._create_openai_client", return_value=object()):
                runtime = build_query_filter_runtime(
                    mode="llm",
                    threshold=0.60,
                    raw_query="CeO2",
                    plan=plan,
                    llm_scoring_prompt="是否是催化领域（如果跟TAP实验有关就更好）的论文。",
                )
                session.add(
                    LLMQueryFilterDropped(
                        doi="10.1000/cached-drop",
                        decision_scope_hash=runtime.llm_decision_scope_hash,
                        decision_scope_text=runtime.llm_decision_scope_text,
                        score=0.11,
                        reason="历史已判定为领域无关",
                        model_name="qwen-plus",
                        prompt_tokens=7,
                        completion_tokens=3,
                        total_tokens=10,
                    )
                )
                session.commit()
                runtime.prepare(session, [record], logger=logs.append)
                with patch("apps.services.query_filtering._score_record_with_llm") as mock_score:
                    matched, reason = runtime.match(record, session=session, logger=logs.append)

        self.assertFalse(matched)
        self.assertEqual(reason, "query_llm_cached_drop")
        mock_score.assert_not_called()
        self.assertTrue(any("sqlite_drop_cache" in line for line in logs))

    def test_llm_mode_can_ignore_sqlite_drop_cache_when_requested(self) -> None:
        plan = QueryPlan(
            raw_input="CeO2",
            must_terms=[],
            should_terms=[],
            exclude_terms=[],
            phrases=[],
            used_ai=False,
            passthrough_query="CeO2",
        )
        record = _record(doi="10.1000/recheck-drop", title="CeO2 catalysis", abstract="TAP reactor study")

        with self.SessionLocal() as session:
            with patch("apps.services.query_filtering._create_openai_client", return_value=object()):
                runtime = build_query_filter_runtime(
                    mode="llm",
                    threshold=0.60,
                    raw_query="CeO2",
                    plan=plan,
                    llm_use_cached_drop=False,
                )
                session.add(
                    LLMQueryFilterDropped(
                        doi="10.1000/recheck-drop",
                        decision_scope_hash=runtime.llm_decision_scope_hash,
                        decision_scope_text=runtime.llm_decision_scope_text,
                        score=0.10,
                        reason="历史已 drop",
                        model_name="qwen-plus",
                    )
                )
                session.commit()
                runtime.prepare(session, [record])
                with patch(
                    "apps.services.query_filtering._score_record_with_llm",
                    return_value=(0.91, "rechecked keep", LLMTokenUsage(6, 2, 8), "qwen-plus"),
                ) as mock_score:
                    matched, reason = runtime.match(record, session=session)

        self.assertTrue(matched)
        self.assertEqual(reason, "matched")
        mock_score.assert_called_once()

    def test_llm_mode_falls_back_to_backup_model_after_primary_failure(self) -> None:
        plan = QueryPlan(
            raw_input="CeO2",
            must_terms=[],
            should_terms=[],
            exclude_terms=[],
            phrases=[],
            used_ai=False,
            passthrough_query="CeO2",
        )
        record = _record(doi="10.1000/fallback", title="CeO2 catalysis", abstract="TAP reactor")
        logs: list[str] = []

        with patch.object(settings, "query_filter_llm_fallback_models", ["qwen-turbo"]):
            with patch("apps.services.query_filtering._create_openai_client", return_value=object()):
                with patch(
                    "apps.services.query_filtering._score_record_with_llm",
                    side_effect=[
                        RuntimeError("quota exceeded"),
                        (0.82, "备用模型判定通过", LLMTokenUsage(6, 2, 8), "qwen-turbo"),
                    ],
                ) as mock_score:
                    runtime = build_query_filter_runtime(
                        mode="llm",
                        threshold=0.60,
                        raw_query="CeO2",
                        plan=plan,
                    )
                    matched, reason = runtime.match(record, logger=logs.append)

        self.assertTrue(matched)
        self.assertEqual(reason, "matched")
        self.assertEqual(mock_score.call_count, 2)
        self.assertEqual(mock_score.call_args_list[0].kwargs["model_name"], runtime.llm_model_candidates[0])
        self.assertEqual(mock_score.call_args_list[1].kwargs["model_name"], "qwen-turbo")
        self.assertEqual(runtime.llm_active_model, "qwen-turbo")
        self.assertTrue(any("自动切换到备用模型 qwen-turbo" in line for line in logs))

    def test_llm_mode_falls_back_to_boolean_without_client(self) -> None:
        query = 'TAP AND microkinetic'
        plan = QueryPlan(
            raw_input=query,
            must_terms=[],
            should_terms=[],
            exclude_terms=[],
            phrases=[],
            used_ai=False,
            passthrough_query=query,
        )
        with patch("apps.services.query_filtering._create_openai_client", return_value=None):
            runtime = build_query_filter_runtime(mode="llm", threshold=0.35, raw_query=query, plan=plan)

        self.assertEqual(runtime.effective_mode, "boolean")
        matched, reason = runtime.match(_record(title="TAP study", abstract="microkinetic reactor"))
        self.assertTrue(matched)
        self.assertEqual(reason, "matched")

    def test_embedding_query_prefers_natural_language_input(self) -> None:
        plan = QueryPlan(
            raw_input="帮我找近五年 TAP 催化和 microkinetic 相关文献",
            must_terms=["TAP", "microkinetic"],
            should_terms=[],
            exclude_terms=[],
            phrases=[],
            used_ai=True,
            passthrough_query=None,
        )

        embedding_text = build_query_embedding_text(plan)

        self.assertEqual(
            embedding_text,
            "帮我找近五年 TAP 催化和 microkinetic 相关文献 || key concepts: TAP; microkinetic",
        )

    def test_embedding_query_uses_positive_terms_for_structured_query(self) -> None:
        plan = QueryPlan(
            raw_input='("temporal analysis of products" OR TAP) AND microkinetic',
            must_terms=[],
            should_terms=[],
            exclude_terms=[],
            phrases=[],
            used_ai=False,
            passthrough_query='("temporal analysis of products" OR TAP) AND microkinetic',
        )

        embedding_text = build_query_embedding_text(plan)

        self.assertEqual(embedding_text, "temporal analysis of products; TAP; microkinetic")

    def test_build_llm_scoring_payload_supports_review_constraints(self) -> None:
        plan = QueryPlan(
            raw_input="CeO2",
            must_terms=["CeO2"],
            should_terms=["TAP"],
            exclude_terms=[],
            phrases=[],
            used_ai=False,
            passthrough_query="CeO2",
        )

        payload = _build_llm_scoring_payload(
            record=_record(doi="10.1000/payload", title="CeO2 catalysis"),
            plan=plan,
            raw_query="CeO2",
            boolean_filter=None,
            llm_scoring_prompt="是否是催化领域（如果跟TAP实验有关就更好）的论文。",
        )

        self.assertEqual(payload["task"], "Score how relevant this candidate paper is to the current search request.")
        self.assertIn("review_constraints", payload)
        self.assertEqual(payload["query"]["raw"], "CeO2")
        self.assertEqual(payload["query"]["domain_objective"], "")
        self.assertEqual(payload["output_schema"]["reason"], "One short reason.")


if __name__ == "__main__":
    unittest.main()
