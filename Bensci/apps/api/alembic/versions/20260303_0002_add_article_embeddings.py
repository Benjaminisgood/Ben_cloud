"""add article embedding cache columns

Revision ID: 20260303_0002
Revises: 20260302_0001
Create Date: 2026-03-03 20:40:00
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260303_0002"
down_revision = "20260302_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("articles", sa.Column("embedding_vector", sa.LargeBinary(), nullable=True))
    op.add_column("articles", sa.Column("embedding_model", sa.String(length=128), nullable=True))
    op.add_column("articles", sa.Column("embedding_dimensions", sa.Integer(), nullable=True))
    op.add_column("articles", sa.Column("embedding_text_hash", sa.String(length=64), nullable=True))
    op.add_column("articles", sa.Column("embedding_updated_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column("articles", "embedding_updated_at")
    op.drop_column("articles", "embedding_text_hash")
    op.drop_column("articles", "embedding_dimensions")
    op.drop_column("articles", "embedding_model")
    op.drop_column("articles", "embedding_vector")
