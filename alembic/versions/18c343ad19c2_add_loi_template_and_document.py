"""add_loi_template_and_document

Revision ID: 18c343ad19c2
Revises: add_participant_response
Create Date: 2025-12-13 00:16:18.000665

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '18c343ad19c2'
down_revision = 'add_participant_response'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create LOI templates table (singleton per tenant)
    op.create_table(
        'loi_templates',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('tenant_id', sa.Integer(), nullable=False),
        sa.Column('template_content', sa.Text(), nullable=True),
        sa.Column('created_by', sa.String(255), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('tenant_id', name='uq_loi_template_tenant')
    )

    # Add indexes
    op.create_index('idx_loi_templates_tenant', 'loi_templates', ['tenant_id'])

    # Add LOI document fields to event_participants
    op.add_column('event_participants',
        sa.Column('loi_document_url', sa.String(500), nullable=True))
    op.add_column('event_participants',
        sa.Column('loi_generated_at', sa.DateTime(), nullable=True))
    op.add_column('event_participants',
        sa.Column('loi_slug', sa.String(255), nullable=True))

    # Add index for LOI slug (for public URL lookups)
    op.create_index('idx_event_participants_loi_slug', 'event_participants', ['loi_slug'], unique=True)


def downgrade() -> None:
    # Drop indexes
    op.drop_index('idx_event_participants_loi_slug', 'event_participants')

    # Remove LOI columns from event_participants
    op.drop_column('event_participants', 'loi_slug')
    op.drop_column('event_participants', 'loi_generated_at')
    op.drop_column('event_participants', 'loi_document_url')

    # Drop LOI templates table
    op.drop_index('idx_loi_templates_tenant', 'loi_templates')
    op.drop_table('loi_templates')