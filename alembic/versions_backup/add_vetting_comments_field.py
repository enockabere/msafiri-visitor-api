"""Add vetting_comments field to event_participants

Revision ID: add_vetting_comments
Revises: 8ce945d8c682
Create Date: 2025-01-27 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'add_vetting_comments'
down_revision = '8ce945d8c682'
branch_labels = None
depends_on = None

def upgrade():
    # Add vetting_comments field to event_participants table
    op.add_column('event_participants', sa.Column('vetting_comments', sa.Text(), nullable=True))

def downgrade():
    # Remove vetting_comments field from event_participants table
    op.drop_column('event_participants', 'vetting_comments')