"""create perdiem setup table

Revision ID: 067_create_perdiem_setup
Revises: 066_add_currency_column
Create Date: 2024-01-01 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '067_create_perdiem_setup'
down_revision = '066_add_currency_column'
branch_labels = None
depends_on = None

def upgrade():
    # Create perdiem_setup table
    op.create_table('perdiem_setup',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('tenant_id', sa.Integer(), nullable=False),
        sa.Column('daily_rate', sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column('currency', sa.String(length=10), nullable=False),
        sa.Column('modified_by', sa.String(255), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_perdiem_setup_id'), 'perdiem_setup', ['id'], unique=False)

def downgrade():
    op.drop_index(op.f('ix_perdiem_setup_id'), table_name='perdiem_setup')
    op.drop_table('perdiem_setup')