"""Add contact_type column to line_manager_recommendations

Revision ID: 007_add_contact_type
Revises: 006_add_line_manager_recommendations
Create Date: 2026-01-12 12:50:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '029_add_contact_type'
down_revision = '028_add_travel_preference_fields'
branch_labels = None
depends_on = None

def upgrade():
    # Add contact_type column to line_manager_recommendations table
    op.add_column('line_manager_recommendations', 
                  sa.Column('contact_type', sa.String(50), nullable=True, default='Line Manager'))

def downgrade():
    # Remove contact_type column
    op.drop_column('line_manager_recommendations', 'contact_type')