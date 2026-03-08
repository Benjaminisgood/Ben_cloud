"""Initial credentials table.

Revision ID: 001
Revises: 
Create Date: 2026-03-08

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '001'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create credentials table
    op.create_table('credentials',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('credential_type', sa.String(length=100), nullable=False),
        sa.Column('encrypted_data', sa.Text(), nullable=False),
        sa.Column('service_name', sa.String(length=255), nullable=True),
        sa.Column('username', sa.String(length=255), nullable=True),
        sa.Column('endpoint', sa.String(length=500), nullable=True),
        sa.Column('category', sa.String(length=100), nullable=True),
        sa.Column('tags', sa.Text(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, default=True),
        sa.Column('last_rotated', sa.DateTime(), nullable=True),
        sa.Column('rotation_reminder_days', sa.Integer(), nullable=True, default=90),
        sa.Column('created_at', sa.DateTime(), nullable=False, default=sa.func.utcnow()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, default=sa.func.utcnow(), onupdate=sa.func.utcnow()),
        sa.Column('accessed_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create index on name for faster lookups
    op.create_index('ix_credentials_name', 'credentials', ['name'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_credentials_name', table_name='credentials')
    op.drop_table('credentials')
