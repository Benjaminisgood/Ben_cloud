"""add_user_project_access

Revision ID: 20260307_0002
Revises: 20260306_0001
Create Date: 2026-03-07 01:05:00+00:00
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20260307_0002"
down_revision = "20260306_0001"
branch_labels = None
depends_on = None


def _table_exists(table_name: str) -> bool:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return table_name in inspector.get_table_names()


def _index_exists(table_name: str, index_name: str) -> bool:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return any(idx["name"] == index_name for idx in inspector.get_indexes(table_name))


def upgrade() -> None:
    if not _table_exists("user_project_access"):
        op.create_table(
            "user_project_access",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("user_id", sa.Integer(), nullable=False),
            sa.Column("project_id", sa.String(length=64), nullable=False),
            sa.Column("granted_by", sa.String(length=80), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(["user_id"], ["user.id"]),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("user_id", "project_id", name="uq_user_project_access_user_project"),
        )
    if _table_exists("user_project_access") and not _index_exists(
        "user_project_access",
        "ix_user_project_access_user_id",
    ):
        op.create_index("ix_user_project_access_user_id", "user_project_access", ["user_id"], unique=False)
    if _table_exists("user_project_access") and not _index_exists(
        "user_project_access",
        "ix_user_project_access_project_id",
    ):
        op.create_index("ix_user_project_access_project_id", "user_project_access", ["project_id"], unique=False)
    if _table_exists("user_project_access") and not _index_exists(
        "user_project_access",
        "ix_user_project_access_user_project",
    ):
        op.create_index(
            "ix_user_project_access_user_project",
            "user_project_access",
            ["user_id", "project_id"],
            unique=False,
        )


def downgrade() -> None:
    if _table_exists("user_project_access") and _index_exists(
        "user_project_access",
        "ix_user_project_access_user_project",
    ):
        op.drop_index("ix_user_project_access_user_project", table_name="user_project_access")
    if _table_exists("user_project_access") and _index_exists(
        "user_project_access",
        "ix_user_project_access_project_id",
    ):
        op.drop_index("ix_user_project_access_project_id", table_name="user_project_access")
    if _table_exists("user_project_access") and _index_exists(
        "user_project_access",
        "ix_user_project_access_user_id",
    ):
        op.drop_index("ix_user_project_access_user_id", table_name="user_project_access")
    if _table_exists("user_project_access"):
        op.drop_table("user_project_access")
