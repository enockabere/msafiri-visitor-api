"""Add accommodation_setup_id field only

Revision ID: d65a944eccd6
Revises: bec22112b245
Create Date: 2025-10-23 12:10:27.475852

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'd65a944eccd6'
down_revision = 'bec22112b245'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add accommodation_setup_id column to events table
    op.add_column('events', sa.Column('accommodation_setup_id', sa.Integer(), nullable=True))
    op.create_foreign_key(None, 'events', 'vendor_event_accommodations', ['accommodation_setup_id'], ['id'])


def downgrade() -> None:
    # Remove accommodation_setup_id column from events table
    op.drop_constraint(None, 'events', type_='foreignkey')
    op.drop_column('events', 'accommodation_setup_id')