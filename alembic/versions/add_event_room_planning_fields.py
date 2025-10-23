"""Add event room planning fields

Revision ID: add_event_room_planning
Revises: 
Create Date: 2024-01-01 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'add_event_room_planning'
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    # Add new room planning fields to events table
    op.add_column('events', sa.Column('expected_participants', sa.Integer(), nullable=True))
    op.add_column('events', sa.Column('single_rooms', sa.Integer(), nullable=True))
    op.add_column('events', sa.Column('double_rooms', sa.Integer(), nullable=True))

def downgrade():
    # Remove room planning fields
    op.drop_column('events', 'double_rooms')
    op.drop_column('events', 'single_rooms')
    op.drop_column('events', 'expected_participants')