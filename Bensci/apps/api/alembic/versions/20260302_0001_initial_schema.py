"""initial schema with tasks and fts5

Revision ID: 20260302_0001
Revises:
Create Date: 2026-03-02 22:45:00
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20260302_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "articles",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("doi", sa.String(length=255), nullable=False, unique=True),
        sa.Column("title", sa.Text(), nullable=False, server_default=""),
        sa.Column("keywords", sa.Text(), nullable=False, server_default=""),
        sa.Column("abstract", sa.Text(), nullable=False, server_default=""),
        sa.Column("journal", sa.String(length=512), nullable=False, server_default=""),
        sa.Column("corresponding_author", sa.String(length=512), nullable=False, server_default=""),
        sa.Column("affiliations", sa.Text(), nullable=False, server_default=""),
        sa.Column("source", sa.String(length=128), nullable=False, server_default=""),
        sa.Column("publisher", sa.String(length=256), nullable=False, server_default=""),
        sa.Column("published_date", sa.String(length=32), nullable=False, server_default=""),
        sa.Column("url", sa.Text(), nullable=False, server_default=""),
        sa.Column("check_status", sa.String(length=16), nullable=False, server_default="unchecked"),
        sa.Column("citation_count", sa.Integer(), nullable=True),
        sa.Column("impact_factor", sa.Float(), nullable=True),
        sa.Column("ingested_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
    )
    op.create_index("ix_articles_doi", "articles", ["doi"], unique=True)

    op.create_table(
        "tags",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.UniqueConstraint("name", name="uq_tag_name"),
    )
    op.create_index("ix_tags_name", "tags", ["name"], unique=False)

    op.create_table(
        "article_tags",
        sa.Column("article_id", sa.Integer(), sa.ForeignKey("articles.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("tag_id", sa.Integer(), sa.ForeignKey("tags.id", ondelete="CASCADE"), primary_key=True),
    )

    op.create_table(
        "tasks",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("task_type", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False, server_default="queued"),
        sa.Column("payload_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("result_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("log_text", sa.Text(), nullable=False, server_default=""),
        sa.Column("error", sa.Text(), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
    )
    op.create_index("ix_tasks_task_type", "tasks", ["task_type"], unique=False)
    op.create_index("ix_tasks_status", "tasks", ["status"], unique=False)

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


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS articles_fts_au")
    op.execute("DROP TRIGGER IF EXISTS articles_fts_ad")
    op.execute("DROP TRIGGER IF EXISTS articles_fts_ai")
    op.execute("DROP TABLE IF EXISTS articles_fts")

    op.drop_index("ix_tasks_status", table_name="tasks")
    op.drop_index("ix_tasks_task_type", table_name="tasks")
    op.drop_table("tasks")

    op.drop_table("article_tags")

    op.drop_index("ix_tags_name", table_name="tags")
    op.drop_table("tags")

    op.drop_index("ix_articles_doi", table_name="articles")
    op.drop_table("articles")
