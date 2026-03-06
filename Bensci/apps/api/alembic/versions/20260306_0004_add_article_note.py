"""add article note column

Revision ID: 20260306_0004
Revises: 20260304_0003_add_llm_query_filter_cache_tables
Create Date: 2026-03-06 16:40:00
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20260306_0004"
down_revision = "20260304_0003_add_llm_query_filter_cache_tables"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("articles", sa.Column("note", sa.Text(), nullable=False, server_default=""))


def downgrade() -> None:
    op.drop_column("articles", "note")

