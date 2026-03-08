
"""initial_journal_tables

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
        "journal_days",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("entry_date", sa.Date(), nullable=False),
        sa.Column("stt_text", sa.Text(), nullable=False, server_default=""),
        sa.Column("entry_text", sa.Text(), nullable=False, server_default=""),
        sa.Column("segment_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_audio_bytes", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("storage_provider", sa.String(length=40), nullable=False, server_default="local"),
        sa.Column("storage_status", sa.String(length=20), nullable=False, server_default="pending"),
        sa.Column("transcript_status", sa.String(length=20), nullable=False, server_default="pending"),
        sa.Column("combined_audio_path", sa.String(length=500), nullable=True),
        sa.Column("combined_audio_object_key", sa.String(length=255), nullable=True),
        sa.Column("combined_audio_url", sa.String(length=500), nullable=True),
        sa.Column("last_error_message", sa.Text(), nullable=False, server_default=""),
        sa.Column("last_recorded_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_transcribed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by", sa.String(length=80), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_by", sa.String(length=80), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_journal_days")),
        sa.UniqueConstraint("entry_date", name=op.f("uq_journal_days_entry_date")),
    )
    op.create_index(op.f("ix_journal_days_entry_date"), "journal_days", ["entry_date"], unique=False)

    op.create_table(
        "journal_audio_segments",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("journal_day_id", sa.Integer(), nullable=False),
        sa.Column("sequence_no", sa.Integer(), nullable=False),
        sa.Column("original_filename", sa.String(length=255), nullable=False),
        sa.Column("file_extension", sa.String(length=20), nullable=False),
        sa.Column("mime_type", sa.String(length=120), nullable=False),
        sa.Column("local_path", sa.String(length=500), nullable=False),
        sa.Column("byte_size", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_by", sa.String(length=80), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["journal_day_id"],
            ["journal_days.id"],
            name=op.f("fk_journal_audio_segments_journal_day_id_journal_days"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_journal_audio_segments")),
    )
    op.create_index(
        op.f("ix_journal_audio_segments_journal_day_id"),
        "journal_audio_segments",
        ["journal_day_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_journal_audio_segments_journal_day_id"), table_name="journal_audio_segments")
    op.drop_table("journal_audio_segments")
    op.drop_index(op.f("ix_journal_days_entry_date"), table_name="journal_days")
    op.drop_table("journal_days")
