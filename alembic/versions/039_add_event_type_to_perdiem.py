"""add event_type to perdiem_requests

Revision ID: 039_add_event_type_to_perdiem
Revises: 038_fix_perdiem_enum_values
Create Date: 2024-01-21 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '039_add_event_type_to_perdiem'
down_revision = '038_fix_perdiem_enum_values'
branch_labels = None
depends_on = None

def upgrade():
    # Add event_type column to perdiem_requests table
    op.add_column('perdiem_requests', sa.Column('event_type', sa.String(100), nullable=True))

def downgrade():
    # Remove event_type column from perdiem_requests table
    op.drop_column('perdiem_requests', 'event_type')