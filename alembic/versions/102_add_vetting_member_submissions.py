"""Add vetting member submissions table

Revision ID: 102
Revises: 101_ensure_vetting_roles_in_enum
Create Date: 2026-02-07

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '102_add_vetting_member_submissions'
down_revision = '101_ensure_vetting_roles_in_enum'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create vetting_member_submissions table
    op.create_table(
        'vetting_member_submissions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('event_id', sa.Integer(), nullable=False),
        sa.Column('member_email', sa.String(length=255), nullable=False),
        sa.Column('submitted_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['event_id'], ['events.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('event_id', 'member_email', name='unique_member_event_submission')
    )
    op.create_index(op.f('ix_vetting_member_submissions_id'), 'vetting_member_submissions', ['id'], unique=False)
    op.create_index(op.f('ix_vetting_member_submissions_event_id'), 'vetting_member_submissions', ['event_id'], unique=False)
    op.create_index(op.f('ix_vetting_member_submissions_member_email'), 'vetting_member_submissions', ['member_email'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_vetting_member_submissions_member_email'), table_name='vetting_member_submissions')
    op.drop_index(op.f('ix_vetting_member_submissions_event_id'), table_name='vetting_member_submissions')
    op.drop_index(op.f('ix_vetting_member_submissions_id'), table_name='vetting_member_submissions')
    op.drop_table('vetting_member_submissions')
