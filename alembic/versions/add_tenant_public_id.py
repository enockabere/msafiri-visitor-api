"""Add public_id to tenants

Revision ID: add_tenant_public_id
Revises: 
Create Date: 2024-01-01 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
import string
import random

# revision identifiers
revision = 'add_tenant_public_id'
down_revision = None
depends_on = None

def generate_random_id(length=12):
    """Generate random alphanumeric string"""
    chars = string.ascii_letters + string.digits
    return ''.join(random.choice(chars) for _ in range(length))

def upgrade():
    # Add public_id column
    op.add_column('tenants', sa.Column('public_id', sa.String(12), nullable=True))
    
    # Generate random IDs for existing tenants
    connection = op.get_bind()
    result = connection.execute(sa.text("SELECT id FROM tenants"))
    for row in result:
        tenant_id = row[0]
        public_id = generate_random_id()
        connection.execute(
            sa.text("UPDATE tenants SET public_id = :public_id WHERE id = :id"),
            {"public_id": public_id, "id": tenant_id}
        )
    
    # Make column non-nullable and add unique constraint
    op.alter_column('tenants', 'public_id', nullable=False)
    op.create_unique_constraint('uq_tenants_public_id', 'tenants', ['public_id'])
    op.create_index('ix_tenants_public_id', 'tenants', ['public_id'])

def downgrade():
    op.drop_index('ix_tenants_public_id', 'tenants')
    op.drop_constraint('uq_tenants_public_id', 'tenants')
    op.drop_column('tenants', 'public_id')