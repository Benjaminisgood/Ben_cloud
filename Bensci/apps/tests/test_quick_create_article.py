from __future__ import annotations

import unittest
from unittest.mock import patch

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from apps.api.routers.articles import quick_create_article
from apps.db.models import Base
from apps.models.schemas import ArticleCreate, QuickArticleCreate
from apps.services.article_service import create_article, get_article_or_none


class QuickCreateArticleTests(unittest.TestCase):
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

    def test_reuse_existing_article_merges_tags(self) -> None:
        with self.SessionLocal() as session:
            existing = create_article(session, ArticleCreate(doi="10.1000/reuse", tags=["tap", "kinetics"]))
            session.commit()

            with patch(
                "apps.api.routers.articles.enrich_article_by_id",
                return_value={
                    "article_id": existing.id,
                    "doi": existing.doi,
                    "skipped": True,
                    "filled_fields": [],
                    "metadata_filled": [],
                    "ai_filled": [],
                    "embedding_generated": False,
                },
            ):
                response = quick_create_article(
                    QuickArticleCreate(doi="10.1000/reuse", tags=["surface"]),
                    session,
                )

            refreshed = get_article_or_none(session, existing.id)

        self.assertIsNotNone(refreshed)
        assert refreshed is not None
        self.assertCountEqual([tag.name for tag in refreshed.tags], ["tap", "kinetics", "surface"])
        self.assertCountEqual([tag.name for tag in response.article.tags], ["tap", "kinetics", "surface"])
        self.assertTrue(any("标签已合并" in line for line in response.logs))

    def test_reuse_existing_article_with_empty_tags_keeps_original_tags(self) -> None:
        with self.SessionLocal() as session:
            existing = create_article(session, ArticleCreate(doi="10.1000/reuse-empty", tags=["tap"]))
            session.commit()

            with patch(
                "apps.api.routers.articles.enrich_article_by_id",
                return_value={
                    "article_id": existing.id,
                    "doi": existing.doi,
                    "skipped": True,
                    "filled_fields": [],
                    "metadata_filled": [],
                    "ai_filled": [],
                    "embedding_generated": False,
                },
            ):
                response = quick_create_article(
                    QuickArticleCreate(doi="10.1000/reuse-empty", tags=[]),
                    session,
                )

            refreshed = get_article_or_none(session, existing.id)

        self.assertIsNotNone(refreshed)
        assert refreshed is not None
        self.assertEqual([tag.name for tag in refreshed.tags], ["tap"])
        self.assertEqual([tag.name for tag in response.article.tags], ["tap"])
        self.assertTrue(any("未输入新标签" in line for line in response.logs))

    def test_insert_only_new_article_skips_enrichment_and_saves_note(self) -> None:
        with self.SessionLocal() as session:
            with patch("apps.api.routers.articles.enrich_article_by_id") as mock_enrich:
                response = quick_create_article(
                    QuickArticleCreate(
                        doi="10.1000/insert-only",
                        tags=["tap"],
                        note="来自项目 A 的初筛记录。",
                        run_enrichment=False,
                    ),
                    session,
                )

            refreshed = get_article_or_none(session, response.article.id)

        self.assertIsNotNone(refreshed)
        assert refreshed is not None
        mock_enrich.assert_not_called()
        self.assertEqual(refreshed.note, "来自项目 A 的初筛记录。")
        self.assertEqual(response.enrichment_result.get("insert_only"), True)
        self.assertTrue(any("仅录入模式" in line for line in response.logs))

    def test_reuse_existing_article_merges_note_without_duplicate_lines(self) -> None:
        with self.SessionLocal() as session:
            existing = create_article(
                session,
                ArticleCreate(
                    doi="10.1000/reuse-note",
                    tags=["tap"],
                    note="复核催化剂配比\n记录首轮结论",
                ),
            )
            session.commit()

            response = quick_create_article(
                QuickArticleCreate(
                    doi="10.1000/reuse-note",
                    tags=[],
                    note="记录首轮结论\n补充实验温度",
                    run_enrichment=False,
                ),
                session,
            )

            refreshed = get_article_or_none(session, existing.id)

        self.assertIsNotNone(refreshed)
        assert refreshed is not None
        self.assertEqual(refreshed.note, "复核催化剂配比\n记录首轮结论\n\n补充实验温度")
        self.assertEqual(response.article.note, "复核催化剂配比\n记录首轮结论\n\n补充实验温度")
        self.assertTrue(any("备注已补充" in line for line in response.logs))


if __name__ == "__main__":
    unittest.main()
