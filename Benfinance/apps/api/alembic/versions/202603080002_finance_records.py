"""finance_records

Revision ID: 202603080002
Revises: 202603080001
Create Date: 2026-03-08 00:14:00+00:00
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
        "finance_records",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("record_type", sa.String(length=24), nullable=False),
        sa.Column("title", sa.String(length=160), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("category", sa.String(length=80), nullable=False),
        sa.Column("flow_direction", sa.String(length=24), nullable=False, server_default="neutral"),
        sa.Column("planning_status", sa.String(length=24), nullable=False, server_default="planned"),
        sa.Column("risk_level", sa.String(length=24), nullable=False, server_default="medium"),
        sa.Column("amount", sa.Float(), nullable=True),
        sa.Column("currency", sa.String(length=8), nullable=False, server_default="CNY"),
        sa.Column("account_name", sa.String(length=120), nullable=True),
        sa.Column("counterparty", sa.String(length=120), nullable=True),
        sa.Column("occurred_on", sa.Date(), nullable=True),
        sa.Column("due_on", sa.Date(), nullable=True),
        sa.Column("next_review_on", sa.Date(), nullable=True),
        sa.Column("recurrence_rule", sa.String(length=120), nullable=True),
        sa.Column("follow_up_action", sa.Text(), nullable=True),
        sa.Column("agent_note", sa.Text(), nullable=True),
        sa.Column("created_by", sa.String(length=80), nullable=False),
        sa.Column("updated_by", sa.String(length=80), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_finance_records")),
    )
    op.create_index(op.f("ix_finance_records_record_type"), "finance_records", ["record_type"], unique=False)
    op.create_index(op.f("ix_finance_records_category"), "finance_records", ["category"], unique=False)
    op.create_index(op.f("ix_finance_records_planning_status"), "finance_records", ["planning_status"], unique=False)
    op.create_index(op.f("ix_finance_records_risk_level"), "finance_records", ["risk_level"], unique=False)
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
    op.drop_index(op.f("ix_finance_records_risk_level"), table_name="finance_records")
    op.drop_index(op.f("ix_finance_records_planning_status"), table_name="finance_records")
    op.drop_index(op.f("ix_finance_records_category"), table_name="finance_records")
    op.drop_index(op.f("ix_finance_records_record_type"), table_name="finance_records")
    op.drop_table("finance_records")
