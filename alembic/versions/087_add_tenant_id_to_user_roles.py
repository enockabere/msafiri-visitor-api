"""Add tenant_id to user_roles table for multi-tenant role support

Revision ID: 087_add_tenant_id
Revises: 086_fix_direct_messages_id_sequence
Create Date: 2026-01-30

This migration adds tenant_id column to user_roles table to support
users having different roles in different tenants.
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic
revision = '087_add_tenant_id'
down_revision = '086fix_dm_seq'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add tenant_id column to user_roles table
    op.add_column('user_roles', sa.Column('tenant_id', sa.String(), nullable=True))

    # Add foreign key constraint
    op.create_foreign_key(
        'fk_user_roles_tenant_id',
        'user_roles',
        'tenants',
        ['tenant_id'],
        ['slug'],
        ondelete='CASCADE'
    )

    # Create index for tenant_id
    op.create_index('ix_user_roles_tenant_id', 'user_roles', ['tenant_id'])

    # Create composite index for user_id and tenant_id
    op.create_index('ix_user_roles_user_tenant', 'user_roles', ['user_id', 'tenant_id'])

    # Drop the old unique constraint (user_id, role)
    try:
        op.drop_constraint('unique_user_role', 'user_roles', type_='unique')
    except Exception as e:
        print(f"Warning: Could not drop old constraint: {e}")

    # Create new unique constraint (user_id, role, tenant_id)
    # This allows the same user to have the same role in different tenants
    op.create_unique_constraint(
        'unique_user_role_tenant',
        'user_roles',
        ['user_id', 'role', 'tenant_id']
    )


def downgrade() -> None:
    # Drop new unique constraint
    op.drop_constraint('unique_user_role_tenant', 'user_roles', type_='unique')

    # Recreate old unique constraint
    op.create_unique_constraint('unique_user_role', 'user_roles', ['user_id', 'role'])

    # Drop indexes
    op.drop_index('ix_user_roles_user_tenant', 'user_roles')
    op.drop_index('ix_user_roles_tenant_id', 'user_roles')

    # Drop foreign key constraint
    op.drop_constraint('fk_user_roles_tenant_id', 'user_roles', type_='foreignkey')

    # Drop tenant_id column
    op.drop_column('user_roles', 'tenant_id')
