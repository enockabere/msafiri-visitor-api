"""Add user_roles table for multi-role support

Revision ID: 040_add_user_roles_table
Revises: 039_fix_vetting_enum_values
Create Date: 2025-01-20 19:30:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = '040_add_user_roles_table'
down_revision = '039_fix_vetting_enum_values'
branch_labels = None
depends_on = None

def upgrade():
    # Create user_roles table
    op.create_table('user_roles',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('role', sa.Enum('SUPER_ADMIN', 'MT_ADMIN', 'HR_ADMIN', 'EVENT_ADMIN', 'VETTING_COMMITTEE', 'VETTING_APPROVER', 'VISITOR', 'GUEST', 'STAFF', name='roletype'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('created_by', sa.String(255), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', 'role', name='unique_user_role')
    )
    
    # Create indexes
    op.create_index('ix_user_roles_user_id', 'user_roles', ['user_id'])
    op.create_index('ix_user_roles_role', 'user_roles', ['role'])
    
    # Migrate existing roles from users table to user_roles table
    op.execute("""
        INSERT INTO user_roles (user_id, role, created_at)
        SELECT id, role, created_at FROM users WHERE role IS NOT NULL
    """)

def downgrade():
    op.drop_index('ix_user_roles_role', table_name='user_roles')
    op.drop_index('ix_user_roles_user_id', table_name='user_roles')
    op.drop_table('user_roles')