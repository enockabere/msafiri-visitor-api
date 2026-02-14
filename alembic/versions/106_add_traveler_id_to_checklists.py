"""add traveler_id to checklists

Revision ID: 106
Revises: 105
Create Date: 2024-01-15 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '106'
down_revision = '105'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('travel_request_checklists', sa.Column('traveler_id', sa.Integer(), nullable=True))
    op.create_index(op.f('ix_travel_request_checklists_traveler_id'), 'travel_request_checklists', ['traveler_id'], unique=False)
    op.create_foreign_key('fk_travel_request_checklists_traveler_id', 'travel_request_checklists', 'travel_request_travelers', ['traveler_id'], ['id'], ondelete='CASCADE')


def downgrade():
    op.drop_constraint('fk_travel_request_checklists_traveler_id', 'travel_request_checklists', type_='foreignkey')
    op.drop_index(op.f('ix_travel_request_checklists_traveler_id'), table_name='travel_request_checklists')
    op.drop_column('travel_request_checklists', 'traveler_id')
