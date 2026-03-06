"""add note column to articles fts objects

Revision ID: 20260306_0005
Revises: 20260306_0004
Create Date: 2026-03-06 17:05:00
"""
from __future__ import annotations

from alembic import op


revision = "20260306_0005"
down_revision = "20260306_0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS articles_fts_au")
    op.execute("DROP TRIGGER IF EXISTS articles_fts_ad")
    op.execute("DROP TRIGGER IF EXISTS articles_fts_ai")
    op.execute("DROP TABLE IF EXISTS articles_fts")

    op.execute(
        "CREATE VIRTUAL TABLE IF NOT EXISTS articles_fts USING fts5("
        "article_id UNINDEXED, "
        "doi, title, keywords, abstract, journal, corresponding_author, affiliations, publisher, note)"
    )
    op.execute(
        "CREATE TRIGGER IF NOT EXISTS articles_fts_ai AFTER INSERT ON articles BEGIN "
        "INSERT INTO articles_fts(article_id, doi, title, keywords, abstract, journal, corresponding_author, affiliations, publisher, note) "
        "VALUES (new.id, COALESCE(new.doi,''), COALESCE(new.title,''), COALESCE(new.keywords,''), COALESCE(new.abstract,''), "
        "COALESCE(new.journal,''), COALESCE(new.corresponding_author,''), COALESCE(new.affiliations,''), COALESCE(new.publisher,''), COALESCE(new.note,'')); "
        "END"
    )
    op.execute(
        "CREATE TRIGGER IF NOT EXISTS articles_fts_ad AFTER DELETE ON articles BEGIN "
        "DELETE FROM articles_fts WHERE article_id = old.id; "
        "END"
    )
    op.execute(
        "CREATE TRIGGER IF NOT EXISTS articles_fts_au AFTER UPDATE ON articles BEGIN "
        "DELETE FROM articles_fts WHERE article_id = old.id; "
        "INSERT INTO articles_fts(article_id, doi, title, keywords, abstract, journal, corresponding_author, affiliations, publisher, note) "
        "VALUES (new.id, COALESCE(new.doi,''), COALESCE(new.title,''), COALESCE(new.keywords,''), COALESCE(new.abstract,''), "
        "COALESCE(new.journal,''), COALESCE(new.corresponding_author,''), COALESCE(new.affiliations,''), COALESCE(new.publisher,''), COALESCE(new.note,'')); "
        "END"
    )
    op.execute(
        "INSERT INTO articles_fts(article_id, doi, title, keywords, abstract, journal, corresponding_author, affiliations, publisher, note) "
        "SELECT id, COALESCE(doi,''), COALESCE(title,''), COALESCE(keywords,''), COALESCE(abstract,''), COALESCE(journal,''), "
        "COALESCE(corresponding_author,''), COALESCE(affiliations,''), COALESCE(publisher,''), COALESCE(note,'') "
        "FROM articles"
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS articles_fts_au")
    op.execute("DROP TRIGGER IF EXISTS articles_fts_ad")
    op.execute("DROP TRIGGER IF EXISTS articles_fts_ai")
    op.execute("DROP TABLE IF EXISTS articles_fts")

    op.execute(
        "CREATE VIRTUAL TABLE IF NOT EXISTS articles_fts USING fts5("
        "article_id UNINDEXED, "
        "doi, title, keywords, abstract, journal, corresponding_author, affiliations, publisher)"
    )
    op.execute(
        "CREATE TRIGGER IF NOT EXISTS articles_fts_ai AFTER INSERT ON articles BEGIN "
        "INSERT INTO articles_fts(article_id, doi, title, keywords, abstract, journal, corresponding_author, affiliations, publisher) "
        "VALUES (new.id, COALESCE(new.doi,''), COALESCE(new.title,''), COALESCE(new.keywords,''), COALESCE(new.abstract,''), "
        "COALESCE(new.journal,''), COALESCE(new.corresponding_author,''), COALESCE(new.affiliations,''), COALESCE(new.publisher,'')); "
        "END"
    )
    op.execute(
        "CREATE TRIGGER IF NOT EXISTS articles_fts_ad AFTER DELETE ON articles BEGIN "
        "DELETE FROM articles_fts WHERE article_id = old.id; "
        "END"
    )
    op.execute(
        "CREATE TRIGGER IF NOT EXISTS articles_fts_au AFTER UPDATE ON articles BEGIN "
        "DELETE FROM articles_fts WHERE article_id = old.id; "
        "INSERT INTO articles_fts(article_id, doi, title, keywords, abstract, journal, corresponding_author, affiliations, publisher) "
        "VALUES (new.id, COALESCE(new.doi,''), COALESCE(new.title,''), COALESCE(new.keywords,''), COALESCE(new.abstract,''), "
        "COALESCE(new.journal,''), COALESCE(new.corresponding_author,''), COALESCE(new.affiliations,''), COALESCE(new.publisher,'')); "
        "END"
    )
    op.execute(
        "INSERT INTO articles_fts(article_id, doi, title, keywords, abstract, journal, corresponding_author, affiliations, publisher) "
        "SELECT id, COALESCE(doi,''), COALESCE(title,''), COALESCE(keywords,''), COALESCE(abstract,''), COALESCE(journal,''), "
        "COALESCE(corresponding_author,''), COALESCE(affiliations,''), COALESCE(publisher,'') "
        "FROM articles"
    )

