"""Add gender column to users table

Revision ID: add_gender_column
Revises: add_updated_by_to_roles
Create Date: 2025-01-27 15:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = 'add_gender_column'
down_revision = 'add_updated_by_to_roles'
branch_labels = None
depends_on = None

def upgrade():
    # Create the gender enum type first
    gender_enum = sa.Enum('male', 'female', 'other', name='gender')
    gender_enum.create(op.get_bind())
    
    # Add gender column to users table
    op.add_column('users', sa.Column('gender', gender_enum, nullable=True))

def downgrade():
    # Remove gender column from users table
    op.drop_column('users', 'gender')
    # Drop the enum type
    op.execute("DROP TYPE IF EXISTS gender")