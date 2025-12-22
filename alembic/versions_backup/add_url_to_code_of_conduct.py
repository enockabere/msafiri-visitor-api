"""add url to code of conduct

Revision ID: add_url_to_code_of_conduct
Revises: 
Create Date: 2024-12-20 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = 'add_url_to_code_of_conduct'
down_revision = None  # Will be set by alembic
branch_labels = None
depends_on = None

def upgrade():
    # Add url column to code_of_conduct table
    op.add_column('code_of_conduct', sa.Column('url', sa.String(500), nullable=True))
    
    # Make content nullable since we can now use URL instead
    op.alter_column('code_of_conduct', 'content', nullable=True)

def downgrade():
    # Remove url column
    op.drop_column('code_of_conduct', 'url')
    
    # Make content non-nullable again
    op.alter_column('code_of_conduct', 'content', nullable=False)