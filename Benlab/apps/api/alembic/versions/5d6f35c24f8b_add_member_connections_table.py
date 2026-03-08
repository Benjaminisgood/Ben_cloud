"""add_member_connections_table

Revision ID: 5d6f35c24f8b
Revises: d150b57c2b59
Create Date: 2026-03-08 15:20:00.000000+00:00
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "5d6f35c24f8b"
down_revision = "d150b57c2b59"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "member_connections",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("source_member_id", sa.Integer(), nullable=False),
        sa.Column("target_member_id", sa.Integer(), nullable=False),
        sa.Column("relation_type", sa.String(length=40), nullable=False),
        sa.Column("closeness", sa.Integer(), nullable=True),
        sa.Column("note", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(
            ["source_member_id"],
            ["members.id"],
            name=op.f("fk_member_connections_source_member_id_members"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["target_member_id"],
            ["members.id"],
            name=op.f("fk_member_connections_target_member_id_members"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_member_connections")),
        sa.UniqueConstraint("source_member_id", "target_member_id", name="uq_member_connections_source_target"),
    )
    op.create_index(
        op.f("ix_member_connections_source_member_id"),
        "member_connections",
        ["source_member_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_member_connections_target_member_id"),
        "member_connections",
        ["target_member_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_member_connections_target_member_id"), table_name="member_connections")
    op.drop_index(op.f("ix_member_connections_source_member_id"), table_name="member_connections")
    op.drop_table("member_connections")
