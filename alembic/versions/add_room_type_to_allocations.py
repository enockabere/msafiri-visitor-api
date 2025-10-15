"""Add room_type to accommodation_allocations

Revision ID: add_room_type_to_allocations
Revises: 
Create Date: 2024-12-19 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'add_room_type_to_allocations'
down_revision = None  # Update this with the latest revision ID
branch_labels = None
depends_on = None

def upgrade():
    # Add room_type column to accommodation_allocations table
    op.add_column('accommodation_allocations', sa.Column('room_type', sa.String(20), nullable=True))

def downgrade():
    # Remove room_type column from accommodation_allocations table
    op.drop_column('accommodation_allocations', 'room_type')