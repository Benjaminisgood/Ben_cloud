from __future__ import annotations

import unittest

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from apps.db.models import Article, Base, LLMQueryFilterDropped, LLMQueryFilterKept
from apps.services.query_filter_cache_service import list_dropped_query_filter_entries, rescue_dropped_query_filter_entry


class QueryFilterCacheServiceTests(unittest.TestCase):
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

    def test_list_dropped_entries_returns_scope_summary_and_article_title(self) -> None:
        with self.SessionLocal() as session:
            session.add(Article(doi="10.1000/drop-one", title="Recovered title", check_status="unchecked"))
            session.add(
                LLMQueryFilterDropped(
                    doi="10.1000/drop-one",
                    decision_scope_hash="scope-a",
                    decision_scope_text='{"kind":"custom_prompt","prompt":"是否是催化领域"}',
                    score=0.12,
                    reason="领域无关",
                    model_name="qwen-plus",
                    prompt_tokens=10,
                    completion_tokens=4,
                    total_tokens=14,
                )
            )
            session.commit()

            items, total = list_dropped_query_filter_entries(session, limit=50)

        self.assertEqual(total, 1)
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0].doi, "10.1000/drop-one")
        self.assertEqual(items[0].article_title, "Recovered title")
        self.assertEqual(items[0].scope_summary, "领域提示词：是否是催化领域")

    def test_rescue_moves_entry_from_drop_to_keep(self) -> None:
        with self.SessionLocal() as session:
            session.add(
                LLMQueryFilterDropped(
                    doi="10.1000/drop-two",
                    decision_scope_hash="scope-b",
                    decision_scope_text='{"kind":"query_relevance","raw_query":"CeO2"}',
                    score=0.08,
                    reason="主题无关",
                    model_name="qwen-plus",
                    prompt_tokens=8,
                    completion_tokens=2,
                    total_tokens=10,
                )
            )
            session.commit()
            dropped = session.scalar(select(LLMQueryFilterDropped).where(LLMQueryFilterDropped.doi == "10.1000/drop-two"))
            assert dropped is not None

            kept = rescue_dropped_query_filter_entry(session, entry_id=dropped.id)
            session.commit()

            kept_row = session.scalar(select(LLMQueryFilterKept).where(LLMQueryFilterKept.doi == "10.1000/drop-two"))
            dropped_row = session.scalar(select(LLMQueryFilterDropped).where(LLMQueryFilterDropped.doi == "10.1000/drop-two"))

        self.assertIsNotNone(kept)
        self.assertIsNotNone(kept_row)
        self.assertIsNone(dropped_row)
        assert kept_row is not None
        self.assertEqual(kept_row.model_name, "manual_rescue")
        self.assertIn("手动救回", kept_row.reason)


if __name__ == "__main__":
    unittest.main()
