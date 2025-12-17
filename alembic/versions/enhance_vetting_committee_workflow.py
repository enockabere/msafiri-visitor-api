"""Enhance vetting committee workflow with multi-role support

Revision ID: enhance_vetting_workflow
Revises: 78d0c1c5934b
Create Date: 2025-12-15 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'enhance_vetting_workflow'
down_revision = '78d0c1c5934b'
branch_labels = None
depends_on = None

def upgrade():
    # Create vetting_email_templates table
    op.create_table('vetting_email_templates',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('committee_id', sa.Integer(), nullable=False),
        sa.Column('template_type', sa.String(50), nullable=False),
        sa.Column('subject', sa.String(255), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('created_by', sa.String(255), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.ForeignKeyConstraint(['committee_id'], ['vetting_committees.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_vetting_email_templates_committee', 'vetting_email_templates', ['committee_id'])
    op.create_index('idx_vetting_email_templates_type', 'vetting_email_templates', ['template_type'])

    # Create vetting_role_assignments table
    op.create_table('vetting_role_assignments',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('committee_id', sa.Integer(), nullable=False),
        sa.Column('role_type', sa.String(50), nullable=False),
        sa.Column('removed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('is_active', sa.Boolean(), default=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['committee_id'], ['vetting_committees.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', 'committee_id', 'role_type')
    )
    op.create_index('idx_vetting_role_assignments_user', 'vetting_role_assignments', ['user_id'])
    op.create_index('idx_vetting_role_assignments_committee', 'vetting_role_assignments', ['committee_id'])
    op.create_index('idx_vetting_role_assignments_active', 'vetting_role_assignments', ['is_active'])

    # Create vetting_deadline_reminders table
    op.create_table('vetting_deadline_reminders',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('committee_id', sa.Integer(), nullable=False),
        sa.Column('reminder_type', sa.String(50), nullable=False),
        sa.Column('recipients_count', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.ForeignKeyConstraint(['committee_id'], ['vetting_committees.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('committee_id', 'reminder_type')
    )

    # Add new columns to vetting_committees table
    op.add_column('vetting_committees', sa.Column('email_notifications_enabled', sa.Boolean(), default=False))
    op.add_column('vetting_committees', sa.Column('selected_template_id', sa.Integer(), nullable=True))
    op.add_column('vetting_committees', sa.Column('not_selected_template_id', sa.Integer(), nullable=True))
    op.add_column('vetting_committees', sa.Column('reminders_sent', sa.Boolean(), default=False))

    # Add foreign key constraints for template references
    op.create_foreign_key(
        'fk_vetting_committees_selected_template',
        'vetting_committees', 'vetting_email_templates',
        ['selected_template_id'], ['id']
    )
    op.create_foreign_key(
        'fk_vetting_committees_not_selected_template',
        'vetting_committees', 'vetting_email_templates',
        ['not_selected_template_id'], ['id']
    )

    # Add new columns to vetting_committee_members table
    op.add_column('vetting_committee_members', sa.Column('had_previous_role', sa.String(50), nullable=True))
    op.add_column('vetting_committee_members', sa.Column('role_removed_at', sa.DateTime(timezone=True), nullable=True))

def downgrade():
    # Remove columns from vetting_committee_members
    op.drop_column('vetting_committee_members', 'role_removed_at')
    op.drop_column('vetting_committee_members', 'had_previous_role')

    # Remove foreign key constraints from vetting_committees
    op.drop_constraint('fk_vetting_committees_not_selected_template', 'vetting_committees', type_='foreignkey')
    op.drop_constraint('fk_vetting_committees_selected_template', 'vetting_committees', type_='foreignkey')

    # Remove columns from vetting_committees
    op.drop_column('vetting_committees', 'reminders_sent')
    op.drop_column('vetting_committees', 'not_selected_template_id')
    op.drop_column('vetting_committees', 'selected_template_id')
    op.drop_column('vetting_committees', 'email_notifications_enabled')

    # Drop new tables
    op.drop_table('vetting_deadline_reminders')
    op.drop_table('vetting_role_assignments')
    op.drop_table('vetting_email_templates')
