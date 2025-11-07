"""Add driver and vehicle details to transport requests

Revision ID: add_transport_driver_details
Revises: 
Create Date: 2024-01-15 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'add_transport_driver_details'
down_revision = '960676794f01'
branch_labels = None
depends_on = None


def upgrade():
    # Add driver and vehicle details columns to transport_requests table
    op.add_column('transport_requests', sa.Column('driver_name', sa.String(255), nullable=True))
    op.add_column('transport_requests', sa.Column('driver_phone', sa.String(50), nullable=True))
    op.add_column('transport_requests', sa.Column('vehicle_number', sa.String(50), nullable=True))
    op.add_column('transport_requests', sa.Column('vehicle_color', sa.String(50), nullable=True))
    op.add_column('transport_requests', sa.Column('booking_reference', sa.String(100), nullable=True))


def downgrade():
    # Remove the added columns
    op.drop_column('transport_requests', 'booking_reference')
    op.drop_column('transport_requests', 'vehicle_color')
    op.drop_column('transport_requests', 'vehicle_number')
    op.drop_column('transport_requests', 'driver_phone')
    op.drop_column('transport_requests', 'driver_name')