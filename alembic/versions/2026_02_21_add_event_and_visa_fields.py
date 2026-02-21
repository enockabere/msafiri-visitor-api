"""Add event_id and visa_assistance_required fields to travel_requests

Revision ID: 2026_02_21_event_visa
Revises: 2025_02_18_backfill
Create Date: 2026-02-21

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '2026_02_21_event_visa'
down_revision = '2025_02_18_backfill'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add event_id to link travel request to an event (for event-related travel)
    op.add_column('travel_requests',
        sa.Column('event_id', sa.Integer(), nullable=True))

    # Add foreign key constraint
    op.create_foreign_key(
        'fk_travel_requests_event_id',
        'travel_requests',
        'events',
        ['event_id'],
        ['id'],
        ondelete='SET NULL'
    )

    # Create index for event_id
    op.create_index('ix_travel_requests_event_id', 'travel_requests', ['event_id'])

    # Add visa_assistance_required field
    op.add_column('travel_requests',
        sa.Column('visa_assistance_required', sa.Boolean(), nullable=False, server_default='false'))


def downgrade() -> None:
    op.drop_column('travel_requests', 'visa_assistance_required')
    op.drop_index('ix_travel_requests_event_id', table_name='travel_requests')
    op.drop_constraint('fk_travel_requests_event_id', 'travel_requests', type_='foreignkey')
    op.drop_column('travel_requests', 'event_id')
