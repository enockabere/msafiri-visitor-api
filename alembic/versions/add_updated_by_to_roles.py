"""Add updated_by column to roles table

Revision ID: add_updated_by_to_roles
Revises: 
Create Date: 2024-12-19

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = 'add_updated_by_to_roles'
down_revision = 'create_roles_table'
depends_on = None

def upgrade():
    # Check if roles table exists before adding column
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    
    if 'roles' in inspector.get_table_names():
        # Add updated_by column to roles table
        op.add_column('roles', sa.Column('updated_by', sa.String(255), nullable=True))
    else:
        # Table doesn't exist, skip this migration
        pass

def downgrade():
    # Check if roles table exists before dropping column
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    
    if 'roles' in inspector.get_table_names():
        # Remove updated_by column from roles table
        op.drop_column('roles', 'updated_by')
    else:
        # Table doesn't exist, skip this migration
        pass