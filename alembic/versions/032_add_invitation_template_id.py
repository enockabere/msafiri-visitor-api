"""Add invitation_template_id to events

Revision ID: 032_add_invitation_template_id
Revises: 031_add_badge_public_id_column
Create Date: 2026-01-16 09:15:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '032_add_invitation_template_id'
down_revision = ('030_fix_participant_certificates', '031_add_badge_public_id')
branch_labels = None
depends_on = None


def upgrade():
    # Add invitation_template_id column to events table
    op.add_column('events', sa.Column('invitation_template_id', sa.Integer(), nullable=True))
    op.create_foreign_key(
        'fk_events_invitation_template_id',
        'events', 'invitation_templates',
        ['invitation_template_id'], ['id']
    )


def downgrade():
    # Remove foreign key and column
    op.drop_constraint('fk_events_invitation_template_id', 'events', type_='foreignkey')
    op.drop_column('events', 'invitation_template_id')
