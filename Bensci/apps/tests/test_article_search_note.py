from __future__ import annotations

import unittest

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from apps.db.models import Base
from apps.models.schemas import ArticleCreate
from apps.services.article_service import create_article, list_articles


class ArticleSearchNoteTests(unittest.TestCase):
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

    def test_search_matches_note_field(self) -> None:
        with self.SessionLocal() as session:
            article = create_article(
                session,
                ArticleCreate(
                    doi="10.1000/note-search",
                    title="A paper without keyword",
                    note="需要重点复核 TAP 脉冲实验条件。",
                ),
            )
            session.commit()

            # Build a minimal FTS table entry that does NOT contain the keyword,
            # so this test validates note matching from the base table branch.
            session.execute(
                text(
                    "CREATE VIRTUAL TABLE articles_fts USING fts5("
                    "article_id UNINDEXED, "
                    "doi, title, keywords, abstract, journal, corresponding_author, affiliations, publisher, note)"
                )
            )
            session.execute(
                text(
                    "INSERT INTO articles_fts(article_id, doi, title, keywords, abstract, journal, corresponding_author, affiliations, publisher, note) "
                    "VALUES (:article_id, :doi, :title, '', '', '', '', '', '', '')"
                ),
                {
                    "article_id": article.id,
                    "doi": article.doi,
                    "title": "not-related",
                },
            )
            session.commit()

            items, total = list_articles(
                session,
                search="脉冲",
                source=None,
                journal=None,
                tags=[],
                offset=0,
                limit=50,
            )

        self.assertEqual(total, 1)
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0].id, article.id)


if __name__ == "__main__":
    unittest.main()

