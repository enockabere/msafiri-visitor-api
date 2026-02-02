"""Add accommodation rates to perdiem_setup

Revision ID: 090_add_accommodation_rates
Revises: 089_add_accommodation_fields_to_perdiem
Create Date: 2026-02-02 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '090_add_accommodation_rates'
down_revision = '089_add_accommodation_fields_to_perdiem'
branch_labels = None
depends_on = None

def upgrade():
    # Add accommodation rate columns to perdiem_setup table
    op.add_column('perdiem_setup', sa.Column('fullboard_rate', sa.Numeric(10, 2), nullable=True, server_default='0'))
    op.add_column('perdiem_setup', sa.Column('halfboard_rate', sa.Numeric(10, 2), nullable=True, server_default='0'))
    op.add_column('perdiem_setup', sa.Column('bed_and_breakfast_rate', sa.Numeric(10, 2), nullable=True, server_default='0'))
    op.add_column('perdiem_setup', sa.Column('bed_only_rate', sa.Numeric(10, 2), nullable=True, server_default='0'))

def downgrade():
    op.drop_column('perdiem_setup', 'bed_only_rate')
    op.drop_column('perdiem_setup', 'bed_and_breakfast_rate')
    op.drop_column('perdiem_setup', 'halfboard_rate')
    op.drop_column('perdiem_setup', 'fullboard_rate')
