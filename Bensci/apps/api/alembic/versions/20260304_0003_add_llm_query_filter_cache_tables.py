"""add llm query filter keep/drop cache tables

Revision ID: 20260304_0003
Revises: 20260303_0002
Create Date: 2026-03-04 22:30:00
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260304_0003"
down_revision = "20260303_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "llm_query_filter_kept",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("doi", sa.String(length=255), nullable=False),
        sa.Column("decision_scope_hash", sa.String(length=64), nullable=False),
        sa.Column("decision_scope_text", sa.Text(), nullable=False, server_default=""),
        sa.Column("score", sa.Float(), nullable=True),
        sa.Column("reason", sa.Text(), nullable=False, server_default=""),
        sa.Column("model_name", sa.String(length=128), nullable=False, server_default=""),
        sa.Column("prompt_tokens", sa.Integer(), nullable=True),
        sa.Column("completion_tokens", sa.Integer(), nullable=True),
        sa.Column("total_tokens", sa.Integer(), nullable=True),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("doi", "decision_scope_hash", name="uq_llm_query_filter_kept_doi_scope"),
    )
    op.create_index(op.f("ix_llm_query_filter_kept_doi"), "llm_query_filter_kept", ["doi"], unique=False)
    op.create_index(
        op.f("ix_llm_query_filter_kept_decision_scope_hash"),
        "llm_query_filter_kept",
        ["decision_scope_hash"],
        unique=False,
    )

    op.create_table(
        "llm_query_filter_dropped",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("doi", sa.String(length=255), nullable=False),
        sa.Column("decision_scope_hash", sa.String(length=64), nullable=False),
        sa.Column("decision_scope_text", sa.Text(), nullable=False, server_default=""),
        sa.Column("score", sa.Float(), nullable=True),
        sa.Column("reason", sa.Text(), nullable=False, server_default=""),
        sa.Column("model_name", sa.String(length=128), nullable=False, server_default=""),
        sa.Column("prompt_tokens", sa.Integer(), nullable=True),
        sa.Column("completion_tokens", sa.Integer(), nullable=True),
        sa.Column("total_tokens", sa.Integer(), nullable=True),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("doi", "decision_scope_hash", name="uq_llm_query_filter_dropped_doi_scope"),
    )
    op.create_index(op.f("ix_llm_query_filter_dropped_doi"), "llm_query_filter_dropped", ["doi"], unique=False)
    op.create_index(
        op.f("ix_llm_query_filter_dropped_decision_scope_hash"),
        "llm_query_filter_dropped",
        ["decision_scope_hash"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_llm_query_filter_dropped_decision_scope_hash"), table_name="llm_query_filter_dropped")
    op.drop_index(op.f("ix_llm_query_filter_dropped_doi"), table_name="llm_query_filter_dropped")
    op.drop_table("llm_query_filter_dropped")

    op.drop_index(op.f("ix_llm_query_filter_kept_decision_scope_hash"), table_name="llm_query_filter_kept")
    op.drop_index(op.f("ix_llm_query_filter_kept_doi"), table_name="llm_query_filter_kept")
    op.drop_table("llm_query_filter_kept")
