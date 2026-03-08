"""preference_records

Revision ID: 202603080002
Revises: 202603080001
Create Date: 2026-03-08 00:10:00+00:00
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "202603080002"
down_revision = "202603080001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "preference_records",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("subject_type", sa.String(length=32), nullable=False),
        sa.Column("subject_name", sa.String(length=160), nullable=False),
        sa.Column("aspect", sa.String(length=80), nullable=False),
        sa.Column("stance", sa.String(length=24), nullable=False),
        sa.Column("timeframe", sa.String(length=24), nullable=False),
        sa.Column("validation_state", sa.String(length=24), nullable=False, server_default="hypothesis"),
        sa.Column("intensity", sa.Integer(), nullable=False, server_default="5"),
        sa.Column("certainty", sa.Integer(), nullable=False, server_default="5"),
        sa.Column("context", sa.String(length=120), nullable=True),
        sa.Column("merchant_name", sa.String(length=160), nullable=True),
        sa.Column("source_kind", sa.String(length=24), nullable=False, server_default="manual"),
        sa.Column("trigger_detail", sa.Text(), nullable=True),
        sa.Column("supporting_detail", sa.Text(), nullable=True),
        sa.Column("valid_from", sa.Date(), nullable=True),
        sa.Column("valid_until", sa.Date(), nullable=True),
        sa.Column("created_by", sa.String(length=80), nullable=False),
        sa.Column("updated_by", sa.String(length=80), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_preference_records")),
    )
    op.create_index(op.f("ix_preference_records_subject_type"), "preference_records", ["subject_type"], unique=False)
    op.create_index(op.f("ix_preference_records_subject_name"), "preference_records", ["subject_name"], unique=False)
    op.create_index(op.f("ix_preference_records_stance"), "preference_records", ["stance"], unique=False)
    op.create_index(op.f("ix_preference_records_timeframe"), "preference_records", ["timeframe"], unique=False)
    op.create_index(op.f("ix_preference_records_validation_state"), "preference_records", ["validation_state"], unique=False)
    op.drop_table("focus_entries")


def downgrade() -> None:
    op.create_table(
        "focus_entries",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=120), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("priority", sa.Integer(), nullable=False, server_default="3"),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="active"),
        sa.Column("created_by", sa.String(length=80), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_focus_entries")),
    )
    op.drop_index(op.f("ix_preference_records_validation_state"), table_name="preference_records")
    op.drop_index(op.f("ix_preference_records_timeframe"), table_name="preference_records")
    op.drop_index(op.f("ix_preference_records_stance"), table_name="preference_records")
    op.drop_index(op.f("ix_preference_records_subject_name"), table_name="preference_records")
    op.drop_index(op.f("ix_preference_records_subject_type"), table_name="preference_records")
    op.drop_table("preference_records")
