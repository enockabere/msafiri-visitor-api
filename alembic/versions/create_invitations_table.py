"""Create invitations table

Revision ID: create_invitations_table
Revises: 
Create Date: 2024-12-19

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = 'create_invitations_table'
down_revision = None
depends_on = None

def upgrade():
    # Create invitations table
    op.create_table('invitations',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('email', sa.String(255), nullable=False, index=True),
        sa.Column('full_name', sa.String(255), nullable=False),
        sa.Column('role', sa.String(50), nullable=False),
        sa.Column('tenant_id', sa.String(), nullable=False, index=True),
        sa.Column('token', sa.String(255), nullable=False, unique=True, index=True),
        sa.Column('expires_at', sa.DateTime(), nullable=False),
        sa.Column('invited_by', sa.String(255), nullable=False),
        sa.Column('accepted_at', sa.DateTime(), nullable=True),
        sa.Column('is_accepted', sa.String(10), default='false'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), onupdate=sa.func.now()),
        sa.PrimaryKeyConstraint('id')
    )

def downgrade():
    # Drop invitations table
    op.drop_table('invitations')