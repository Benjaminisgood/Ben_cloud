"""initial_graph_sync_runs

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
        "graph_sync_runs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("mode", sa.String(length=20), nullable=False, server_default="preview"),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="preview"),
        sa.Column("raw_episode_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("confirmed_episode_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("backend", sa.String(length=40), nullable=False, server_default="preview"),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("created_by", sa.String(length=80), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_graph_sync_runs")),
    )


def downgrade() -> None:
    op.drop_table("graph_sync_runs")
