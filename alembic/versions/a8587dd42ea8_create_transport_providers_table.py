"""create transport providers table

Revision ID: a8587dd42ea8
Revises: e40cbba5b37c
Create Date: 2025-10-25 12:33:59.542221

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'a8587dd42ea8'
down_revision = 'e40cbba5b37c'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table('transport_providers',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('tenant_id', sa.Integer(), nullable=False),
        sa.Column('provider_name', sa.String(length=100), nullable=False),
        sa.Column('is_enabled', sa.Boolean(), nullable=True),
        sa.Column('client_id', sa.String(length=255), nullable=True),
        sa.Column('client_secret', sa.Text(), nullable=True),
        sa.Column('hmac_secret', sa.Text(), nullable=True),
        sa.Column('api_base_url', sa.String(length=255), nullable=True),
        sa.Column('token_url', sa.String(length=255), nullable=True),
        sa.Column('created_by', sa.String(length=255), nullable=False),
        sa.Column('updated_by', sa.String(length=255), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_transport_providers_id'), 'transport_providers', ['id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_transport_providers_id'), table_name='transport_providers')
    op.drop_table('transport_providers')