"""Add updated_by column to roles table

Revision ID: add_updated_by_to_roles
Revises: 
Create Date: 2024-12-19

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = 'add_updated_by_to_roles'
down_revision = 'create_events_table'
depends_on = None

def upgrade():
    # Add updated_by column to roles table
    op.add_column('roles', sa.Column('updated_by', sa.String(255), nullable=True))

def downgrade():
    # Remove updated_by column from roles table
    op.drop_column('roles', 'updated_by')