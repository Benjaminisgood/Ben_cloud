"""initial_video_library

Revision ID: 202603080001
Revises:
Create Date: 2026-03-08 00:00:00+00:00
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "202603080001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "video_items",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("external_id", sa.String(length=120), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("asset_url", sa.Text(), nullable=False),
        sa.Column("poster_url", sa.Text(), nullable=True),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("duration_label", sa.String(length=40), nullable=True),
        sa.Column("library_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="active"),
        sa.Column("trashed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("trashed_by", sa.String(length=80), nullable=True),
        sa.Column("restored_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("restored_by", sa.String(length=80), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_video_items")),
        sa.UniqueConstraint("external_id", name=op.f("uq_video_items_external_id")),
    )
    op.create_index(op.f("ix_video_items_external_id"), "video_items", ["external_id"], unique=True)
    op.create_index(op.f("ix_video_items_status"), "video_items", ["status"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_video_items_status"), table_name="video_items")
    op.drop_index(op.f("ix_video_items_external_id"), table_name="video_items")
    op.drop_table("video_items")
