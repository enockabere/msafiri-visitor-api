"""Add must_change_password field to users table

Revision ID: add_must_change_password
Revises: 
Create Date: 2024-01-01 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = 'add_must_change_password'
down_revision = None  # Update this with the latest revision
branch_labels = None
depends_on = None

def upgrade():
    # Add must_change_password column to users table
    op.add_column('users', sa.Column('must_change_password', sa.Boolean(), nullable=True, default=False))
    
    # Update existing records to have must_change_password = False
    op.execute("UPDATE users SET must_change_password = FALSE WHERE must_change_password IS NULL")
    
    # Make the column non-nullable after setting default values
    op.alter_column('users', 'must_change_password', nullable=False)

def downgrade():
    # Remove must_change_password column
    op.drop_column('users', 'must_change_password')