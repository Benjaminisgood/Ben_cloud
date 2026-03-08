"""Add review workflow columns to credentials.

Revision ID: 002
Revises: 001
Create Date: 2026-03-09
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "credentials",
        sa.Column("review_status", sa.String(length=20), nullable=False, server_default="pending"),
    )
    op.add_column(
        "credentials",
        sa.Column("source", sa.String(length=50), nullable=False, server_default="agent"),
    )
    op.add_column("credentials", sa.Column("source_detail", sa.Text(), nullable=True))
    op.add_column("credentials", sa.Column("review_notes", sa.Text(), nullable=True))
    op.add_column("credentials", sa.Column("reviewed_by", sa.String(length=255), nullable=True))
    op.add_column("credentials", sa.Column("reviewed_at", sa.DateTime(), nullable=True))
    op.add_column(
        "credentials",
        sa.Column("sensitivity", sa.String(length=20), nullable=False, server_default="high"),
    )
    op.add_column(
        "credentials",
        sa.Column("agent_access", sa.String(length=30), nullable=False, server_default="approval_required"),
    )
    op.create_index("ix_credentials_review_status", "credentials", ["review_status"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_credentials_review_status", table_name="credentials")
    op.drop_column("credentials", "agent_access")
    op.drop_column("credentials", "sensitivity")
    op.drop_column("credentials", "reviewed_at")
    op.drop_column("credentials", "reviewed_by")
    op.drop_column("credentials", "review_notes")
    op.drop_column("credentials", "source_detail")
    op.drop_column("credentials", "source")
    op.drop_column("credentials", "review_status")
