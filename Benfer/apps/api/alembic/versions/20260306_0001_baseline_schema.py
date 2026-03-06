"""baseline_schema

Revision ID: 20260306_0001
Revises:
Create Date: 2026-03-06 23:50:00+00:00
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20260306_0001"
down_revision = None
branch_labels = None
depends_on = None


def _table_exists(table_name: str) -> bool:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return table_name in inspector.get_table_names()


def _index_exists(table_name: str, index_name: str) -> bool:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return any(index["name"] == index_name for index in inspector.get_indexes(table_name))


def upgrade() -> None:
    if not _table_exists("clipboard_items"):
        op.create_table(
            "clipboard_items",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("content", sa.Text(), nullable=False),
            sa.Column("content_type", sa.String(length=50), nullable=True),
            sa.Column("user_id", sa.String(length=100), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=True),
            sa.Column("expires_at", sa.DateTime(), nullable=True),
            sa.Column("is_public", sa.Boolean(), nullable=True),
            sa.Column("access_token", sa.String(length=100), nullable=True),
            sa.PrimaryKeyConstraint("id"),
        )

    if _table_exists("clipboard_items") and not _index_exists("clipboard_items", op.f("ix_clipboard_items_id")):
        op.create_index(op.f("ix_clipboard_items_id"), "clipboard_items", ["id"], unique=False)
    if _table_exists("clipboard_items") and not _index_exists("clipboard_items", op.f("ix_clipboard_items_created_at")):
        op.create_index(op.f("ix_clipboard_items_created_at"), "clipboard_items", ["created_at"], unique=False)
    if _table_exists("clipboard_items") and not _index_exists("clipboard_items", op.f("ix_clipboard_items_access_token")):
        op.create_index(op.f("ix_clipboard_items_access_token"), "clipboard_items", ["access_token"], unique=True)

    if not _table_exists("file_uploads"):
        op.create_table(
            "file_uploads",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("filename", sa.String(length=255), nullable=False),
            sa.Column("oss_key", sa.String(length=500), nullable=False),
            sa.Column("file_size", sa.Integer(), nullable=False),
            sa.Column("content_type", sa.String(length=100), nullable=True),
            sa.Column("user_id", sa.String(length=100), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=True),
            sa.Column("expires_at", sa.DateTime(), nullable=True),
            sa.Column("download_count", sa.Integer(), nullable=True),
            sa.Column("access_token", sa.String(length=100), nullable=True),
            sa.Column("upload_status", sa.String(length=20), nullable=True),
            sa.Column("chunk_count", sa.Integer(), nullable=True),
            sa.Column("total_chunks", sa.Integer(), nullable=True),
            sa.PrimaryKeyConstraint("id"),
        )

    if _table_exists("file_uploads") and not _index_exists("file_uploads", op.f("ix_file_uploads_id")):
        op.create_index(op.f("ix_file_uploads_id"), "file_uploads", ["id"], unique=False)
    if _table_exists("file_uploads") and not _index_exists("file_uploads", op.f("ix_file_uploads_created_at")):
        op.create_index(op.f("ix_file_uploads_created_at"), "file_uploads", ["created_at"], unique=False)
    if _table_exists("file_uploads") and not _index_exists("file_uploads", op.f("ix_file_uploads_access_token")):
        op.create_index(op.f("ix_file_uploads_access_token"), "file_uploads", ["access_token"], unique=True)


def downgrade() -> None:
    if _table_exists("file_uploads") and _index_exists("file_uploads", op.f("ix_file_uploads_access_token")):
        op.drop_index(op.f("ix_file_uploads_access_token"), table_name="file_uploads")
    if _table_exists("file_uploads") and _index_exists("file_uploads", op.f("ix_file_uploads_created_at")):
        op.drop_index(op.f("ix_file_uploads_created_at"), table_name="file_uploads")
    if _table_exists("file_uploads") and _index_exists("file_uploads", op.f("ix_file_uploads_id")):
        op.drop_index(op.f("ix_file_uploads_id"), table_name="file_uploads")
    if _table_exists("file_uploads"):
        op.drop_table("file_uploads")

    if _table_exists("clipboard_items") and _index_exists("clipboard_items", op.f("ix_clipboard_items_access_token")):
        op.drop_index(op.f("ix_clipboard_items_access_token"), table_name="clipboard_items")
    if _table_exists("clipboard_items") and _index_exists("clipboard_items", op.f("ix_clipboard_items_created_at")):
        op.drop_index(op.f("ix_clipboard_items_created_at"), table_name="clipboard_items")
    if _table_exists("clipboard_items") and _index_exists("clipboard_items", op.f("ix_clipboard_items_id")):
        op.drop_index(op.f("ix_clipboard_items_id"), table_name="clipboard_items")
    if _table_exists("clipboard_items"):
        op.drop_table("clipboard_items")
