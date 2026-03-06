"""guest booking: make customer_id nullable

Revision ID: a1b2c3d4e5f6
Revises: 9f4b7a1d2c3e
Create Date: 2026-03-01 12:00:00.000000+00:00
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "a1b2c3d4e5f6"
down_revision = "9f4b7a1d2c3e"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # SQLite requires batch mode for ALTER COLUMN
    with op.batch_alter_table("booking") as batch_op:
        batch_op.alter_column(
            "customer_id",
            existing_type=sa.Integer(),
            nullable=True,
        )


def downgrade() -> None:
    with op.batch_alter_table("booking") as batch_op:
        batch_op.alter_column(
            "customer_id",
            existing_type=sa.Integer(),
            nullable=False,
        )
