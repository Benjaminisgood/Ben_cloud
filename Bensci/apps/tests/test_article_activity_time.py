from __future__ import annotations

import unittest
from datetime import datetime

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from apps.db.models import Base
from apps.models.schemas import ArticleCreate, ArticleUpdate
from apps.providers.base import ProviderRecord
from apps.services.article_service import create_article, get_article_or_none, update_article, upsert_provider_record


class ArticleActivityTimeTests(unittest.TestCase):
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

    def test_manual_tag_update_refreshes_activity_time(self) -> None:
        with self.SessionLocal() as session:
            article = create_article(session, ArticleCreate(doi="10.1000/manual-tag-update", tags=["tap"]))
            session.commit()

            baseline = datetime(2024, 1, 1, 0, 0, 0)
            article.ingested_at = baseline
            article.updated_at = baseline
            session.commit()

            current = get_article_or_none(session, article.id)
            self.assertIsNotNone(current)
            assert current is not None

            update_article(session, current, ArticleUpdate(tags=["tap", "kinetics"]))
            session.commit()

            refreshed = get_article_or_none(session, article.id)
            self.assertIsNotNone(refreshed)
            assert refreshed is not None

            self.assertGreater(refreshed.ingested_at, baseline)
            self.assertEqual(refreshed.ingested_at, refreshed.updated_at)
            self.assertCountEqual([tag.name for tag in refreshed.tags], ["tap", "kinetics"])

    def test_provider_upsert_with_new_tag_refreshes_activity_time(self) -> None:
        with self.SessionLocal() as session:
            article = create_article(session, ArticleCreate(doi="10.1000/provider-tag-update", tags=["tap"]))
            session.commit()

            baseline = datetime(2024, 1, 1, 0, 0, 0)
            article.ingested_at = baseline
            article.updated_at = baseline
            session.commit()

            status = upsert_provider_record(
                session,
                ProviderRecord(doi="10.1000/provider-tag-update"),
                save_tags=["surface"],
            )
            session.commit()

            refreshed = get_article_or_none(session, article.id)
            self.assertIsNotNone(refreshed)
            assert refreshed is not None

            self.assertEqual(status, "updated")
            self.assertGreater(refreshed.ingested_at, baseline)
            self.assertEqual(refreshed.ingested_at, refreshed.updated_at)
            self.assertCountEqual([tag.name for tag in refreshed.tags], ["tap", "surface"])

    def test_manual_note_update_refreshes_activity_time(self) -> None:
        with self.SessionLocal() as session:
            article = create_article(session, ArticleCreate(doi="10.1000/manual-note-update"))
            session.commit()

            baseline = datetime(2024, 1, 1, 0, 0, 0)
            article.ingested_at = baseline
            article.updated_at = baseline
            session.commit()

            current = get_article_or_none(session, article.id)
            self.assertIsNotNone(current)
            assert current is not None

            update_article(session, current, ArticleUpdate(note="需要复核实验条件与采样时序。"))
            session.commit()

            refreshed = get_article_or_none(session, article.id)
            self.assertIsNotNone(refreshed)
            assert refreshed is not None

            self.assertEqual(refreshed.note, "需要复核实验条件与采样时序。")
            self.assertGreater(refreshed.ingested_at, baseline)
            self.assertEqual(refreshed.ingested_at, refreshed.updated_at)


if __name__ == "__main__":
    unittest.main()
