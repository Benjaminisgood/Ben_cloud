"""initial vinyl records

Revision ID: 202603080001
Revises:
Create Date: 2026-03-08 20:30:00
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
        "vinyl_records",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=120), nullable=False, server_default=""),
        sa.Column("note", sa.Text(), nullable=False, server_default=""),
        sa.Column("oss_path", sa.String(length=1024), nullable=False),
        sa.Column("added_by", sa.String(length=80), nullable=False),
        sa.Column("is_trashed", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("selected_for_date", sa.Date(), nullable=True),
        sa.Column("tossed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("oss_path"),
    )
    op.create_index(op.f("ix_vinyl_records_is_trashed"), "vinyl_records", ["is_trashed"], unique=False)
    op.create_index(op.f("ix_vinyl_records_selected_for_date"), "vinyl_records", ["selected_for_date"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_vinyl_records_selected_for_date"), table_name="vinyl_records")
    op.drop_index(op.f("ix_vinyl_records_is_trashed"), table_name="vinyl_records")
    op.drop_table("vinyl_records")
