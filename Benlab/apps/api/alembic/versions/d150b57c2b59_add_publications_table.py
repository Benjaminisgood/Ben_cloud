"""add_publications_table

Revision ID: d150b57c2b59
Revises: 43cc4d187676
Create Date: 2026-03-05 05:39:46.716362+00:00
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'd150b57c2b59'
down_revision = '43cc4d187676'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 创建 publications 表
    op.create_table(
        'publications',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('doi', sa.String(length=255), nullable=False),
        sa.Column('title', sa.String(length=500), nullable=False),
        sa.Column('authors', sa.Text(), nullable=True),
        sa.Column('journal', sa.String(length=255), nullable=True),
        sa.Column('publication_year', sa.Integer(), nullable=True),
        sa.Column('abstract', sa.Text(), nullable=True),
        sa.Column('pdf_path', sa.String(length=500), nullable=True),
        sa.Column('pdf_downloaded', sa.Boolean(), nullable=False, default=False),
        sa.Column('download_status', sa.String(length=50), nullable=False, default='pending'),
        sa.Column('download_error', sa.Text(), nullable=True),
        sa.Column('metadata_source', sa.String(length=100), nullable=False, default='manual'),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_publications_doi'), 'publications', ['doi'], unique=True)
    
    # 使用 batch 模式修改 attachments 表（SQLite 需要）
    with op.batch_alter_table('attachments', schema=None) as batch_op:
        batch_op.add_column(sa.Column('publication_id', sa.Integer(), nullable=True))
        batch_op.create_index(op.f('ix_attachments_publication_id'), ['publication_id'], unique=False)
        batch_op.create_foreign_key(
            op.f('fk_attachments_publication_id_publications'),
            'publications',
            ['publication_id'],
            ['id'],
            ondelete='CASCADE'
        )


def downgrade() -> None:
    # 使用 batch 模式删除外键和列（SQLite 需要）
    with op.batch_alter_table('attachments', schema=None) as batch_op:
        batch_op.drop_constraint(op.f('fk_attachments_publication_id_publications'), type_='foreignkey')
        batch_op.drop_index(op.f('ix_attachments_publication_id'))
        batch_op.drop_column('publication_id')
    
    # 删除 publications 表
    op.drop_index(op.f('ix_publications_doi'), table_name='publications')
    op.drop_table('publications')

