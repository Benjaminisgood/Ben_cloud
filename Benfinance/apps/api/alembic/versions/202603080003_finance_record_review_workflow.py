"""finance_record_review_workflow

Revision ID: 202603080003
Revises: 202603080002
Create Date: 2026-03-08 00:24:00+00:00
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "202603080003"
down_revision = "202603080002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "finance_records",
        sa.Column("review_status", sa.String(length=24), nullable=False, server_default="approved"),
    )
    op.add_column("finance_records", sa.Column("review_note", sa.Text(), nullable=True))
    op.add_column("finance_records", sa.Column("reviewed_by", sa.String(length=80), nullable=True))
    op.add_column("finance_records", sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True))
    op.create_index(op.f("ix_finance_records_review_status"), "finance_records", ["review_status"], unique=False)
    op.execute(
        """
        UPDATE finance_records
        SET review_status = 'approved',
            reviewed_by = created_by,
            reviewed_at = created_at
        WHERE review_status IS NULL OR review_status = ''
        """
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_finance_records_review_status"), table_name="finance_records")
    op.drop_column("finance_records", "reviewed_at")
    op.drop_column("finance_records", "reviewed_by")
    op.drop_column("finance_records", "review_note")
    op.drop_column("finance_records", "review_status")
