"""add availability to useful contacts

Revision ID: add_availability_contacts
Revises: 
Create Date: 2025-01-15 10:30:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = 'add_availability_contacts'
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    # Add availability columns to useful_contacts table
    op.add_column('useful_contacts', sa.Column('availability_schedule', sa.String(), nullable=True))
    op.add_column('useful_contacts', sa.Column('availability_details', sa.Text(), nullable=True))

def downgrade():
    op.drop_column('useful_contacts', 'availability_details')
    op.drop_column('useful_contacts', 'availability_schedule')