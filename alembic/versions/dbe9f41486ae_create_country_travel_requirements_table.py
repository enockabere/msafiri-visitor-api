"""create country travel requirements table

Revision ID: dbe9f41486ae
Revises: d65a944eccd6
Create Date: 2025-10-25 11:35:02.970764

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'dbe9f41486ae'
down_revision = 'd65a944eccd6'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create country_travel_requirements table
    op.create_table('country_travel_requirements',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('tenant_id', sa.Integer(), nullable=False),
        sa.Column('country', sa.String(length=100), nullable=False),
        sa.Column('visa_required', sa.Boolean(), nullable=True),
        sa.Column('eta_required', sa.Boolean(), nullable=True),
        sa.Column('passport_required', sa.Boolean(), nullable=True),
        sa.Column('flight_ticket_required', sa.Boolean(), nullable=True),
        sa.Column('created_by', sa.String(length=255), nullable=False),
        sa.Column('updated_by', sa.String(length=255), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('tenant_id', 'country', name='unique_tenant_country')
    )
    op.create_index(op.f('ix_country_travel_requirements_id'), 'country_travel_requirements', ['id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_country_travel_requirements_id'), table_name='country_travel_requirements')
    op.drop_table('country_travel_requirements')