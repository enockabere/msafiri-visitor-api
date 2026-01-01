"""add poa templates

Revision ID: 013_poa_templates
Revises: 012_event_badges
Create Date: 2025-12-27 17:30:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '013_poa_templates'
down_revision = '012_event_badges'
branch_labels = None
depends_on = None


def upgrade():
    # Create poa_templates table
    op.create_table('poa_templates',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('vendor_accommodation_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('template_content', sa.Text(), nullable=False),
        sa.Column('logo_url', sa.String(length=500), nullable=True),
        sa.Column('logo_public_id', sa.String(length=255), nullable=True),
        sa.Column('signature_url', sa.String(length=500), nullable=True),
        sa.Column('signature_public_id', sa.String(length=255), nullable=True),
        sa.Column('enable_qr_code', sa.Boolean(), nullable=True, server_default='true'),
        sa.Column('is_active', sa.Boolean(), nullable=True, server_default='true'),
        sa.Column('tenant_id', sa.Integer(), nullable=False),
        sa.Column('created_by', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['vendor_accommodation_id'], ['vendor_accommodations.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('vendor_accommodation_id', name='uq_poa_template_vendor_accommodation')
    )
    op.create_index(op.f('ix_poa_templates_id'), 'poa_templates', ['id'], unique=False)
    op.create_index(op.f('ix_poa_templates_tenant_id'), 'poa_templates', ['tenant_id'], unique=False)
    op.create_index(op.f('ix_poa_templates_vendor_accommodation_id'), 'poa_templates', ['vendor_accommodation_id'], unique=True)


def downgrade():
    op.drop_index(op.f('ix_poa_templates_vendor_accommodation_id'), table_name='poa_templates')
    op.drop_index(op.f('ix_poa_templates_tenant_id'), table_name='poa_templates')
    op.drop_index(op.f('ix_poa_templates_id'), table_name='poa_templates')
    op.drop_table('poa_templates')
