"""Add registration form fields to public_registrations

Revision ID: 002_add_registration_form_fields
Revises: 001_comprehensive_initial
Create Date: 2024-10-09 15:30:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '002_add_registration_form_fields'
down_revision = '001_add_direct_messages'
branch_labels = None
depends_on = None

def upgrade():
    # Add missing columns to public_registrations table
    op.add_column('public_registrations', sa.Column('dietary_requirements', sa.Text(), nullable=True))
    op.add_column('public_registrations', sa.Column('accommodation_needs', sa.Text(), nullable=True))
    op.add_column('public_registrations', sa.Column('certificate_name', sa.String(255), nullable=True))
    op.add_column('public_registrations', sa.Column('code_of_conduct_confirm', sa.String(10), nullable=True))
    op.add_column('public_registrations', sa.Column('travel_requirements_confirm', sa.String(10), nullable=True))

def downgrade():
    # Remove the added columns
    op.drop_column('public_registrations', 'travel_requirements_confirm')
    op.drop_column('public_registrations', 'code_of_conduct_confirm')
    op.drop_column('public_registrations', 'certificate_name')
    op.drop_column('public_registrations', 'accommodation_needs')
    op.drop_column('public_registrations', 'dietary_requirements')