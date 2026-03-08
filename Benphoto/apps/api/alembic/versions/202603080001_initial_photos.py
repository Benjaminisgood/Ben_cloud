
"""initial_photos

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
        "photos",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=120), nullable=False, server_default=""),
        sa.Column("caption", sa.Text(), nullable=False, server_default=""),
        sa.Column("oss_path", sa.String(length=1024), nullable=False),
        sa.Column("added_by", sa.String(length=80), nullable=False),
        sa.Column("is_trashed", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.Column("selected_for_date", sa.Date(), nullable=True),
        sa.Column("tossed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_photos")),
        sa.UniqueConstraint("oss_path", name=op.f("uq_photos_oss_path")),
    )
    op.create_index(op.f("ix_photos_is_trashed"), "photos", ["is_trashed"], unique=False)
    op.create_index(op.f("ix_photos_selected_for_date"), "photos", ["selected_for_date"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_photos_selected_for_date"), table_name="photos")
    op.drop_index(op.f("ix_photos_is_trashed"), table_name="photos")
    op.drop_table("photos")
