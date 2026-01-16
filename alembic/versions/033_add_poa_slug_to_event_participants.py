"""Add poa_slug to event_participants

Revision ID: 033_add_poa_slug
Revises: 032_add_invitation_template_id
Create Date: 2026-01-16 14:50:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '033_add_poa_slug'
down_revision = '032_add_invitation_template_id'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('event_participants', sa.Column('poa_slug', sa.String(100), nullable=True))
    op.create_unique_constraint('uq_event_participants_poa_slug', 'event_participants', ['poa_slug'])


def downgrade():
    op.drop_constraint('uq_event_participants_poa_slug', 'event_participants', type_='unique')
    op.drop_column('event_participants', 'poa_slug')
