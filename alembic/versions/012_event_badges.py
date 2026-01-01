"""Add event_badges table

Revision ID: 012_event_badges
Revises: 011_avatar_fields
Create Date: 2024-12-24 08:50:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '012_event_badges'
down_revision = '011_avatar_fields'
branch_labels = None
depends_on = None


def upgrade():
    # Create event_badges table
    op.create_table('event_badges',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('event_id', sa.Integer(), nullable=False),
        sa.Column('badge_template_id', sa.Integer(), nullable=False),
        sa.Column('template_variables', sa.JSON(), nullable=False),
        sa.Column('tenant_id', sa.Integer(), nullable=False),
        sa.Column('created_by', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['badge_template_id'], ['badge_templates.id'], ),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], ),
        sa.ForeignKeyConstraint(['event_id'], ['events.id'], ),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_event_badges_event_id'), 'event_badges', ['event_id'], unique=False)
    op.create_index(op.f('ix_event_badges_id'), 'event_badges', ['id'], unique=False)
    op.create_index(op.f('ix_event_badges_tenant_id'), 'event_badges', ['tenant_id'], unique=False)

    # Create participant_badges table
    op.create_table('participant_badges',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('event_badge_id', sa.Integer(), nullable=False),
        sa.Column('participant_id', sa.Integer(), nullable=False),
        sa.Column('badge_url', sa.String(length=500), nullable=True),
        sa.Column('badge_public_id', sa.String(length=255), nullable=True),
        sa.Column('issued_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['event_badge_id'], ['event_badges.id'], ),
        sa.ForeignKeyConstraint(['participant_id'], ['event_participants.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_participant_badges_event_badge_id'), 'participant_badges', ['event_badge_id'], unique=False)
    op.create_index(op.f('ix_participant_badges_id'), 'participant_badges', ['id'], unique=False)
    op.create_index(op.f('ix_participant_badges_participant_id'), 'participant_badges', ['participant_id'], unique=False)


def downgrade():
    op.drop_index(op.f('ix_participant_badges_participant_id'), table_name='participant_badges')
    op.drop_index(op.f('ix_participant_badges_id'), table_name='participant_badges')
    op.drop_index(op.f('ix_participant_badges_event_badge_id'), table_name='participant_badges')
    op.drop_table('participant_badges')
    
    op.drop_index(op.f('ix_event_badges_tenant_id'), table_name='event_badges')
    op.drop_index(op.f('ix_event_badges_id'), table_name='event_badges')
    op.drop_index(op.f('ix_event_badges_event_id'), table_name='event_badges')
    op.drop_table('event_badges')