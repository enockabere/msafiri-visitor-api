"""Create admin_invitations table

Revision ID: create_admin_invitations_table
Revises: add_reply_to_message_id
Create Date: 2024-10-03 11:10:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'create_admin_invitations_table'
down_revision = 'add_reply_to_message_id'
depends_on = None


def upgrade():
    op.create_table('admin_invitations',
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
    op.create_index(op.f('ix_admin_invitations_id'), 'admin_invitations', ['id'], unique=False)
    op.create_index(op.f('ix_admin_invitations_invitation_token'), 'admin_invitations', ['invitation_token'], unique=True)


def downgrade():
    op.drop_index(op.f('ix_admin_invitations_invitation_token'), table_name='admin_invitations')
    op.drop_index(op.f('ix_admin_invitations_id'), table_name='admin_invitations')
    op.drop_index(op.f('ix_admin_invitations_email'), table_name='admin_invitations')
    op.drop_table('admin_invitations')