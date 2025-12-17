"""Add news_updates table only

Revision ID: 7ecda31119dc
Revises: 5ee79a036ab6
Create Date: 2025-10-27 22:51:29.860047

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '7ecda31119dc'
down_revision = '5ee79a036ab6'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create news_updates table
    op.create_table('news_updates',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('tenant_id', sa.Integer(), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('summary', sa.Text(), nullable=False),
        sa.Column('content', sa.Text(), nullable=True),
        sa.Column('category', sa.Enum('HEALTH_PROGRAM', 'SECURITY', 'EVENTS', 'REPORTS', 'GENERAL', 'ANNOUNCEMENT', name='newscategory'), nullable=False),
        sa.Column('is_important', sa.Boolean(), nullable=True),
        sa.Column('is_published', sa.Boolean(), nullable=True),
        sa.Column('image_url', sa.String(length=500), nullable=True),
        sa.Column('created_by', sa.String(length=255), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('published_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_news_updates_id'), 'news_updates', ['id'], unique=False)


def downgrade() -> None:
    # Drop news_updates table
    op.drop_index(op.f('ix_news_updates_id'), table_name='news_updates')
    op.drop_table('news_updates')