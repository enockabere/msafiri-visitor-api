"""add travel request checklists

Revision ID: 105
Revises: 104
Create Date: 2026-01-26 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '105'
down_revision = '103_add_travel_request_approvals'
branch_labels = None
depends_on = None


def upgrade():
    # Create travel_request_checklists table
    op.create_table(
        'travel_request_checklists',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('travel_request_id', sa.Integer(), nullable=False),
        sa.Column('traveler_name', sa.String(255), nullable=False),
        sa.Column('nationality', sa.String(100), nullable=True),
        sa.Column('destination_tenants', postgresql.JSONB(), nullable=True),
        sa.Column('checklist_items', postgresql.JSONB(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['travel_request_id'], ['travel_requests.id'], ondelete='CASCADE'),
    )
    op.create_index('ix_travel_request_checklists_travel_request_id', 'travel_request_checklists', ['travel_request_id'])


def downgrade():
    op.drop_index('ix_travel_request_checklists_travel_request_id', table_name='travel_request_checklists')
    op.drop_table('travel_request_checklists')
