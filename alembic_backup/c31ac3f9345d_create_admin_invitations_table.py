"""create_admin_invitations_table

Revision ID: c31ac3f9345d
Revises: 4a2aaf238a99
Create Date: 2025-10-27 14:20:40.483387

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'c31ac3f9345d'
down_revision = '4a2aaf238a99'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create admin_invitations table
    op.create_table(
        'admin_invitations',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('invitation_token', sa.String(length=255), nullable=False),
        sa.Column('invited_by', sa.String(length=255), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=True),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('accepted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('user_existed', sa.Boolean(), nullable=True),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_admin_invitations_email'), 'admin_invitations', ['email'], unique=False)
    op.create_index(op.f('ix_admin_invitations_invitation_token'), 'admin_invitations', ['invitation_token'], unique=True)


def downgrade() -> None:
    # Drop admin_invitations table
    op.drop_index(op.f('ix_admin_invitations_invitation_token'), table_name='admin_invitations')
    op.drop_index(op.f('ix_admin_invitations_email'), table_name='admin_invitations')
    op.drop_table('admin_invitations')