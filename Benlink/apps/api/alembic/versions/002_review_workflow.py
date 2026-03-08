"""Add review workflow columns to links.

Revision ID: 002
Revises: 001
Create Date: 2026-03-09
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "links",
        sa.Column("review_status", sa.String(length=20), nullable=False, server_default="pending"),
    )
    op.add_column(
        "links",
        sa.Column("source", sa.String(length=50), nullable=False, server_default="agent"),
    )
    op.add_column("links", sa.Column("source_detail", sa.Text(), nullable=True))
    op.add_column("links", sa.Column("review_notes", sa.Text(), nullable=True))
    op.add_column("links", sa.Column("reviewed_by", sa.String(length=255), nullable=True))
    op.add_column("links", sa.Column("reviewed_at", sa.DateTime(), nullable=True))
    op.create_index("ix_links_review_status", "links", ["review_status"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_links_review_status", table_name="links")
    op.drop_column("links", "reviewed_at")
    op.drop_column("links", "reviewed_by")
    op.drop_column("links", "review_notes")
    op.drop_column("links", "source_detail")
    op.drop_column("links", "source")
    op.drop_column("links", "review_status")
