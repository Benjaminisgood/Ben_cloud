"""baseline schema

Revision ID: 9f4b7a1d2c3e
Revises:
Create Date: 2026-03-01 00:00:00.000000+00:00
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "9f4b7a1d2c3e"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "user",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("username", sa.String(length=80), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("role", sa.String(length=32), nullable=False),
        sa.Column("full_name", sa.String(length=80), nullable=False, server_default=""),
        sa.Column("phone", sa.String(length=40), nullable=False, server_default=""),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("1")),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_user_username"), "user", ["username"], unique=True)
    op.create_index(op.f("ix_user_role"), "user", ["role"], unique=False)
    op.create_index(op.f("ix_user_is_active"), "user", ["is_active"], unique=False)

    op.create_table(
        "properties",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=120), nullable=False),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        sa.Column("city", sa.String(length=80), nullable=False, server_default=""),
        sa.Column("address", sa.String(length=255), nullable=False, server_default=""),
        sa.Column("price_per_night", sa.Integer(), nullable=False),
        sa.Column("max_guests", sa.Integer(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("1")),
        sa.Column("created_by_admin_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["created_by_admin_id"], ["user.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_properties_is_active"), "properties", ["is_active"], unique=False)
    op.create_index(op.f("ix_properties_city"), "properties", ["city"], unique=False)

    op.create_table(
        "booking",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("property_id", sa.Integer(), nullable=False),
        sa.Column("customer_id", sa.Integer(), nullable=False),
        sa.Column("check_in_date", sa.Date(), nullable=False),
        sa.Column("check_out_date", sa.Date(), nullable=False),
        sa.Column("total_nights", sa.Integer(), nullable=False),
        sa.Column("guest_count", sa.Integer(), nullable=False),
        sa.Column("guest_name", sa.String(length=80), nullable=False),
        sa.Column("guest_phone", sa.String(length=40), nullable=False),
        sa.Column("note", sa.Text(), nullable=False, server_default=""),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("payment_received", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.Column("payment_confirmed_at", sa.DateTime(), nullable=True),
        sa.Column("review_note", sa.Text(), nullable=False, server_default=""),
        sa.Column("reviewed_by_admin_id", sa.Integer(), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.CheckConstraint("check_out_date > check_in_date", name="ck_booking_checkout_after_checkin"),
        sa.ForeignKeyConstraint(["property_id"], ["properties.id"]),
        sa.ForeignKeyConstraint(["customer_id"], ["user.id"]),
        sa.ForeignKeyConstraint(["reviewed_by_admin_id"], ["user.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_booking_property_id"), "booking", ["property_id"], unique=False)
    op.create_index(op.f("ix_booking_customer_id"), "booking", ["customer_id"], unique=False)
    op.create_index(op.f("ix_booking_status"), "booking", ["status"], unique=False)
    op.create_index(op.f("ix_booking_check_in_date"), "booking", ["check_in_date"], unique=False)
    op.create_index(op.f("ix_booking_check_out_date"), "booking", ["check_out_date"], unique=False)

    op.create_table(
        "booking_night_lock",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("property_id", sa.Integer(), nullable=False),
        sa.Column("booking_id", sa.Integer(), nullable=False),
        sa.Column("stay_date", sa.Date(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["booking_id"], ["booking.id"]),
        sa.ForeignKeyConstraint(["property_id"], ["properties.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("property_id", "stay_date", name="uq_property_stay_date"),
    )
    op.create_index(op.f("ix_booking_night_lock_property_id"), "booking_night_lock", ["property_id"], unique=False)
    op.create_index(op.f("ix_booking_night_lock_stay_date"), "booking_night_lock", ["stay_date"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_booking_night_lock_stay_date"), table_name="booking_night_lock")
    op.drop_index(op.f("ix_booking_night_lock_property_id"), table_name="booking_night_lock")
    op.drop_table("booking_night_lock")

    op.drop_index(op.f("ix_booking_check_out_date"), table_name="booking")
    op.drop_index(op.f("ix_booking_check_in_date"), table_name="booking")
    op.drop_index(op.f("ix_booking_status"), table_name="booking")
    op.drop_index(op.f("ix_booking_customer_id"), table_name="booking")
    op.drop_index(op.f("ix_booking_property_id"), table_name="booking")
    op.drop_table("booking")

    op.drop_index(op.f("ix_properties_city"), table_name="properties")
    op.drop_index(op.f("ix_properties_is_active"), table_name="properties")
    op.drop_table("properties")

    op.drop_index(op.f("ix_user_is_active"), table_name="user")
    op.drop_index(op.f("ix_user_role"), table_name="user")
    op.drop_index(op.f("ix_user_username"), table_name="user")
    op.drop_table("user")
