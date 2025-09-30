"""create_events_table

Revision ID: create_events_table
Revises: create_invitations_table
Create Date: 2025-01-27 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'create_events_table'
down_revision = 'create_invitations_table'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create events table
    op.create_table('events',
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('start_date', sa.Date(), nullable=False),
        sa.Column('end_date', sa.Date(), nullable=False),
        sa.Column('duration_days', sa.Integer(), nullable=False),
        sa.Column('perdiem_rate', sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column('location', sa.String(length=255), nullable=True),
        sa.Column('event_location', sa.String(length=500), nullable=False),
        sa.Column('accommodation_details', sa.Text(), nullable=True),
        sa.Column('event_room_info', sa.Text(), nullable=True),
        sa.Column('food_info', sa.Text(), nullable=True),
        sa.Column('room_rate', sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column('other_facilities', sa.Text(), nullable=True),
        sa.Column('tenant_id', sa.String(), nullable=False),
        sa.Column('created_by', sa.String(length=255), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=True, default=True),
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.slug'], )
    )
    op.create_index(op.f('ix_events_id'), 'events', ['id'], unique=False)
    op.create_index(op.f('ix_events_tenant_id'), 'events', ['tenant_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_events_tenant_id'), table_name='events')
    op.drop_index(op.f('ix_events_id'), table_name='events')
    op.drop_table('events')