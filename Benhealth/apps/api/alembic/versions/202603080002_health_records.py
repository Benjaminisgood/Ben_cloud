"""health_records

Revision ID: 202603080002
Revises: 202603080001
Create Date: 2026-03-08 00:12:00+00:00
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
        "health_records",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("domain", sa.String(length=24), nullable=False),
        sa.Column("title", sa.String(length=160), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("care_status", sa.String(length=24), nullable=False, server_default="active"),
        sa.Column("concern_level", sa.String(length=24), nullable=False, server_default="medium"),
        sa.Column("started_on", sa.Date(), nullable=True),
        sa.Column("ended_on", sa.Date(), nullable=True),
        sa.Column("next_review_on", sa.Date(), nullable=True),
        sa.Column("frequency", sa.String(length=24), nullable=False, server_default="once"),
        sa.Column("metric_name", sa.String(length=80), nullable=True),
        sa.Column("metric_value", sa.Float(), nullable=True),
        sa.Column("metric_unit", sa.String(length=24), nullable=True),
        sa.Column("mood_score", sa.Integer(), nullable=True),
        sa.Column("energy_score", sa.Integer(), nullable=True),
        sa.Column("pain_score", sa.Integer(), nullable=True),
        sa.Column("sleep_hours", sa.Float(), nullable=True),
        sa.Column("food_name", sa.String(length=160), nullable=True),
        sa.Column("exercise_name", sa.String(length=160), nullable=True),
        sa.Column("provider_name", sa.String(length=160), nullable=True),
        sa.Column("medication_name", sa.String(length=160), nullable=True),
        sa.Column("follow_up_plan", sa.Text(), nullable=True),
        sa.Column("agent_note", sa.Text(), nullable=True),
        sa.Column("created_by", sa.String(length=80), nullable=False),
        sa.Column("updated_by", sa.String(length=80), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_health_records")),
    )
    op.create_index(op.f("ix_health_records_domain"), "health_records", ["domain"], unique=False)
    op.create_index(op.f("ix_health_records_care_status"), "health_records", ["care_status"], unique=False)
    op.create_index(op.f("ix_health_records_concern_level"), "health_records", ["concern_level"], unique=False)
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
    op.drop_index(op.f("ix_health_records_concern_level"), table_name="health_records")
    op.drop_index(op.f("ix_health_records_care_status"), table_name="health_records")
    op.drop_index(op.f("ix_health_records_domain"), table_name="health_records")
    op.drop_table("health_records")
