from __future__ import annotations

import unittest
from unittest.mock import patch

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from apps.db.models import Article, Base
from apps.services.ai_enrichment import enrich_article_by_id
from apps.services.enrichment_jobs import _missing_predicate


class AiEnrichmentTests(unittest.TestCase):
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

    def test_single_article_enrichment_can_generate_embedding_on_request(self) -> None:
        with self.SessionLocal() as session:
            article = Article(
                doi="10.1000/embed-me",
                title="TAP kinetics study",
                keywords="TAP; microkinetic",
                abstract="Detailed abstract for embedding generation.",
                journal="Journal of Catalysis",
                corresponding_author="Alice",
                affiliations="Test Lab",
                source="openalex",
                publisher="Elsevier",
                published_date="2025-01-01",
                url="https://example.com/embed-me",
            )
            session.add(article)
            session.commit()

            with (
                patch("apps.services.ai_enrichment._create_openai_client", return_value=object()),
                patch("apps.services.ai_enrichment._embedding_model_name", return_value="test-embedding"),
                patch("apps.services.ai_enrichment._normalize_embedding_dimensions", return_value=3),
                patch("apps.services.ai_enrichment._embedding_vectors", return_value=[[0.1, 0.2, 0.3]]),
            ):
                result = enrich_article_by_id(session, article.id, include_embedding=True)
                session.commit()

            refreshed = session.get(Article, article.id)

        self.assertIsNotNone(refreshed)
        assert refreshed is not None
        self.assertFalse(result["skipped"])
        self.assertTrue(result["embedding_generated"])
        self.assertIn("embedding", result["filled_fields"])
        self.assertEqual(refreshed.embedding_model, "test-embedding")
        self.assertEqual(refreshed.embedding_dimensions, 3)
        self.assertIsNotNone(refreshed.embedding_vector)
        self.assertIsNotNone(refreshed.embedding_text_hash)
        self.assertIsNotNone(refreshed.embedding_updated_at)

    def test_single_article_enrichment_without_embedding_request_keeps_embedding_empty(self) -> None:
        with self.SessionLocal() as session:
            article = Article(
                doi="10.1000/no-embed",
                title="TAP kinetics study",
                keywords="TAP; microkinetic",
                abstract="Detailed abstract for embedding generation.",
                journal="Journal of Catalysis",
                corresponding_author="Alice",
                affiliations="Test Lab",
                source="openalex",
                publisher="Elsevier",
                published_date="2025-01-01",
                url="https://example.com/no-embed",
            )
            session.add(article)
            session.commit()

            result = enrich_article_by_id(session, article.id, include_embedding=False)
            session.commit()

            refreshed = session.get(Article, article.id)

        self.assertIsNotNone(refreshed)
        assert refreshed is not None
        self.assertTrue(result["skipped"])
        self.assertFalse(result["embedding_generated"])
        self.assertEqual(result["filled_fields"], [])
        self.assertIsNone(refreshed.embedding_vector)

    def test_fill_empty_predicate_does_not_treat_missing_embedding_as_missing_metadata(self) -> None:
        with self.SessionLocal() as session:
            complete = Article(
                doi="10.1000/complete",
                title="Complete article",
                keywords="TAP",
                abstract="Abstract",
                journal="Journal",
                corresponding_author="Author",
                affiliations="Lab",
                source="openalex",
                publisher="Publisher",
                published_date="2025-01-01",
                url="https://example.com",
                citation_count=1,
            )
            missing_abstract = Article(
                doi="10.1000/missing-abstract",
                title="Missing abstract article",
                keywords="TAP",
                abstract="",
                journal="Journal",
                corresponding_author="Author",
                affiliations="Lab",
                source="openalex",
                publisher="Publisher",
                published_date="2025-01-01",
                url="https://example.com",
                citation_count=1,
            )
            missing_only_impact_factor = Article(
                doi="10.1000/missing-impact",
                title="Missing impact factor article",
                keywords="TAP",
                abstract="Abstract",
                journal="Journal",
                corresponding_author="Author",
                affiliations="Lab",
                source="openalex",
                publisher="Publisher",
                published_date="2025-01-01",
                url="https://example.com",
                citation_count=1,
            )
            missing_only_citation_count = Article(
                doi="10.1000/missing-citation",
                title="Missing citation count article",
                keywords="TAP",
                abstract="Abstract",
                journal="Journal",
                corresponding_author="Author",
                affiliations="Lab",
                source="openalex",
                publisher="Publisher",
                published_date="2025-01-01",
                url="https://example.com",
                impact_factor=2.0,
            )
            session.add_all([complete, missing_abstract, missing_only_impact_factor, missing_only_citation_count])
            session.commit()

            ids = list(
                session.scalars(
                    select(Article.id)
                    .where(_missing_predicate())
                    .order_by(Article.id.asc())
                )
            )

        self.assertEqual(ids, [missing_abstract.id])


if __name__ == "__main__":
    unittest.main()
