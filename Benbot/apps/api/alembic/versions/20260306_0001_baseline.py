"""baseline_schema

Revision ID: 20260306_0001
Revises:
Create Date: 2026-03-06 20:55:00+00:00
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20260306_0001"
down_revision = None
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
    if not _table_exists("user"):
        op.create_table(
            "user",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("username", sa.String(length=80), nullable=False),
            sa.Column("password_hash", sa.String(length=255), nullable=False),
            sa.Column("role", sa.String(length=32), nullable=False),
            sa.Column("is_active", sa.Boolean(), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("username"),
        )

    if not _table_exists("project_health"):
        op.create_table(
            "project_health",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("project_id", sa.String(length=64), nullable=False),
            sa.Column("status", sa.String(length=16), nullable=False),
            sa.Column("response_ms", sa.Integer(), nullable=True),
            sa.Column("last_checked", sa.DateTime(), nullable=True),
            sa.PrimaryKeyConstraint("id"),
        )
    if _table_exists("project_health") and not _index_exists("project_health", op.f("ix_project_health_project_id")):
        op.create_index(op.f("ix_project_health_project_id"), "project_health", ["project_id"], unique=True)

    if not _table_exists("project_click"):
        op.create_table(
            "project_click",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("project_id", sa.String(length=64), nullable=False),
            sa.Column("click_date", sa.Date(), nullable=False),
            sa.Column("count", sa.Integer(), nullable=False),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("project_id", "click_date", name="uq_project_click_date"),
        )
    if _table_exists("project_click") and not _index_exists("project_click", op.f("ix_project_click_project_id")):
        op.create_index(op.f("ix_project_click_project_id"), "project_click", ["project_id"], unique=False)

    if not _table_exists("bug_report"):
        op.create_table(
            "bug_report",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("reporter_id", sa.Integer(), nullable=False),
            sa.Column("body", sa.Text(), nullable=False),
            sa.Column("status", sa.String(length=32), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("approved_at", sa.DateTime(), nullable=True),
            sa.Column("repaired", sa.Integer(), nullable=True),
            sa.Column("verified", sa.Integer(), nullable=True),
            sa.ForeignKeyConstraint(["reporter_id"], ["user.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
    if _table_exists("bug_report") and not _index_exists("bug_report", "ix_bug_report_status_approved_at"):
        op.create_index(
            "ix_bug_report_status_approved_at",
            "bug_report",
            ["status", "approved_at"],
            unique=False,
        )

    if not _table_exists("project_log"):
        op.create_table(
            "project_log",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("project_id", sa.String(length=64), nullable=False),
            sa.Column("level", sa.String(length=16), nullable=False),
            sa.Column("source", sa.String(length=32), nullable=False),
            sa.Column("message", sa.Text(), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.PrimaryKeyConstraint("id"),
        )
    if _table_exists("project_log") and not _index_exists("project_log", op.f("ix_project_log_project_id")):
        op.create_index(op.f("ix_project_log_project_id"), "project_log", ["project_id"], unique=False)
    if _table_exists("project_log") and not _index_exists("project_log", "ix_project_log_project_created_at"):
        op.create_index(
            "ix_project_log_project_created_at",
            "project_log",
            ["project_id", "created_at"],
            unique=False,
        )


def downgrade() -> None:
    if _table_exists("project_log") and _index_exists("project_log", "ix_project_log_project_created_at"):
        op.drop_index("ix_project_log_project_created_at", table_name="project_log")
    if _table_exists("project_log") and _index_exists("project_log", op.f("ix_project_log_project_id")):
        op.drop_index(op.f("ix_project_log_project_id"), table_name="project_log")
    if _table_exists("project_log"):
        op.drop_table("project_log")

    if _table_exists("bug_report") and _index_exists("bug_report", "ix_bug_report_status_approved_at"):
        op.drop_index("ix_bug_report_status_approved_at", table_name="bug_report")
    if _table_exists("bug_report"):
        op.drop_table("bug_report")

    if _table_exists("project_click") and _index_exists("project_click", op.f("ix_project_click_project_id")):
        op.drop_index(op.f("ix_project_click_project_id"), table_name="project_click")
    if _table_exists("project_click"):
        op.drop_table("project_click")

    if _table_exists("project_health") and _index_exists("project_health", op.f("ix_project_health_project_id")):
        op.drop_index(op.f("ix_project_health_project_id"), table_name="project_health")
    if _table_exists("project_health"):
        op.drop_table("project_health")

    if _table_exists("user"):
        op.drop_table("user")
