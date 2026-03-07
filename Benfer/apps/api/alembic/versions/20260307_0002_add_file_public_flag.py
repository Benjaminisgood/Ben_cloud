"""add_file_public_flag

Revision ID: 20260307_0002
Revises: 20260306_0001
Create Date: 2026-03-07 15:40:00+00:00
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260307_0002"
down_revision = "20260306_0001"
branch_labels = None
depends_on = None


def _table_exists(table_name: str) -> bool:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return table_name in inspector.get_table_names()


def _column_exists(table_name: str, column_name: str) -> bool:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return any(column["name"] == column_name for column in inspector.get_columns(table_name))


def upgrade() -> None:
    if _table_exists("file_uploads") and not _column_exists("file_uploads", "is_public"):
        op.add_column(
            "file_uploads",
            sa.Column("is_public", sa.Boolean(), nullable=False, server_default=sa.false()),
        )


def downgrade() -> None:
    if _table_exists("file_uploads") and _column_exists("file_uploads", "is_public"):
        op.drop_column("file_uploads", "is_public")
