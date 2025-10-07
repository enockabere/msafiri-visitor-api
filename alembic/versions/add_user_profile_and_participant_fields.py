"""Add user profile fields and event participant fields

Revision ID: add_user_profile_fields
Revises: 
Create Date: 2024-10-07 08:30:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'add_user_profile_fields'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # Add new columns to users table
    op.add_column('users', sa.Column('country', sa.String(100), nullable=True))
    op.add_column('users', sa.Column('position', sa.String(255), nullable=True))
    op.add_column('users', sa.Column('project', sa.String(255), nullable=True))
    
    # Add new columns to event_participants table
    op.add_column('event_participants', sa.Column('country', sa.String(100), nullable=True))
    op.add_column('event_participants', sa.Column('position', sa.String(255), nullable=True))
    op.add_column('event_participants', sa.Column('project', sa.String(255), nullable=True))
    op.add_column('event_participants', sa.Column('gender', sa.String(50), nullable=True))
    op.add_column('event_participants', sa.Column('eta', sa.String(255), nullable=True))
    op.add_column('event_participants', sa.Column('requires_eta', sa.Boolean(), default=False))
    op.add_column('event_participants', sa.Column('passport_document', sa.String(500), nullable=True))
    op.add_column('event_participants', sa.Column('ticket_document', sa.String(500), nullable=True))
    
    # Add country column to events table
    op.add_column('events', sa.Column('country', sa.String(100), nullable=True))


def downgrade():
    # Remove columns from events table
    op.drop_column('events', 'country')
    
    # Remove columns from event_participants table
    op.drop_column('event_participants', 'ticket_document')
    op.drop_column('event_participants', 'passport_document')
    op.drop_column('event_participants', 'requires_eta')
    op.drop_column('event_participants', 'eta')
    op.drop_column('event_participants', 'gender')
    op.drop_column('event_participants', 'project')
    op.drop_column('event_participants', 'position')
    op.drop_column('event_participants', 'country')
    
    # Remove columns from users table
    op.drop_column('users', 'project')
    op.drop_column('users', 'position')
    op.drop_column('users', 'country')