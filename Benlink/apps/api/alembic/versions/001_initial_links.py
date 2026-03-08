"""Initial links table.

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
    # Create links table
    op.create_table('links',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('url', sa.String(length=2048), nullable=False),
        sa.Column('title', sa.String(length=500), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('domain', sa.String(length=255), nullable=True),
        sa.Column('favicon_url', sa.String(length=500), nullable=True),
        sa.Column('og_image', sa.String(length=500), nullable=True),
        sa.Column('category', sa.String(length=100), nullable=True),
        sa.Column('tags', sa.Text(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('status', sa.String(length=50), nullable=False, default='unread'),
        sa.Column('priority', sa.String(length=20), nullable=False, default='normal'),
        sa.Column('is_active', sa.Boolean(), nullable=False, default=True),
        sa.Column('is_favorite', sa.Boolean(), nullable=False, default=False),
        sa.Column('created_at', sa.DateTime(), nullable=False, default=sa.func.utcnow()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, default=sa.func.utcnow(), onupdate=sa.func.utcnow()),
        sa.Column('accessed_at', sa.DateTime(), nullable=True),
        sa.Column('last_checked_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('url')
    )
    
    # Create index on url for faster lookups
    op.create_index('ix_links_url', 'links', ['url'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_links_url', table_name='links')
    op.drop_table('links')
