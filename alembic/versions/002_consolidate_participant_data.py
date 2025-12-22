"""consolidate_participant_data

Revision ID: 002_consolidate_participant_data
Revises: 001_initial_schema
Create Date: 2025-01-02 12:01:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '002_consolidate_participant_data'
down_revision = '001_initial_schema'
branch_labels = None
depends_on = None

def upgrade() -> None:
    # Add missing fields from public_registrations to event_participants
    op.add_column('event_participants', sa.Column('first_name', sa.String(length=255), nullable=True))
    op.add_column('event_participants', sa.Column('last_name', sa.String(length=255), nullable=True))
    op.add_column('event_participants', sa.Column('oc', sa.String(length=50), nullable=True))
    op.add_column('event_participants', sa.Column('contract_status', sa.String(length=100), nullable=True))
    op.add_column('event_participants', sa.Column('contract_type', sa.String(length=100), nullable=True))
    op.add_column('event_participants', sa.Column('gender_identity', sa.String(length=100), nullable=True))
    op.add_column('event_participants', sa.Column('sex', sa.String(length=50), nullable=True))
    op.add_column('event_participants', sa.Column('pronouns', sa.String(length=50), nullable=True))
    op.add_column('event_participants', sa.Column('current_position', sa.String(length=255), nullable=True))
    op.add_column('event_participants', sa.Column('country_of_work', sa.String(length=255), nullable=True))
    op.add_column('event_participants', sa.Column('project_of_work', sa.String(length=255), nullable=True))
    op.add_column('event_participants', sa.Column('personal_email', sa.String(length=255), nullable=True))
    op.add_column('event_participants', sa.Column('msf_email', sa.String(length=255), nullable=True))
    op.add_column('event_participants', sa.Column('hrco_email', sa.String(length=255), nullable=True))
    op.add_column('event_participants', sa.Column('career_manager_email', sa.String(length=255), nullable=True))
    op.add_column('event_participants', sa.Column('ld_manager_email', sa.String(length=255), nullable=True))
    op.add_column('event_participants', sa.Column('line_manager_email', sa.String(length=255), nullable=True))
    op.add_column('event_participants', sa.Column('phone_number', sa.String(length=50), nullable=True))
    op.add_column('event_participants', sa.Column('travelling_internationally', sa.String(length=10), nullable=True))
    op.add_column('event_participants', sa.Column('accommodation_needs', sa.Text(), nullable=True))
    op.add_column('event_participants', sa.Column('daily_meals', sa.String(length=255), nullable=True))
    op.add_column('event_participants', sa.Column('certificate_name', sa.String(length=255), nullable=True))
    op.add_column('event_participants', sa.Column('badge_name', sa.String(length=255), nullable=True))
    op.add_column('event_participants', sa.Column('motivation_letter', sa.Text(), nullable=True))
    op.add_column('event_participants', sa.Column('code_of_conduct_confirm', sa.String(length=10), nullable=True))
    op.add_column('event_participants', sa.Column('travel_requirements_confirm', sa.String(length=10), nullable=True))

def downgrade() -> None:
    # Remove the added columns
    op.drop_column('event_participants', 'travel_requirements_confirm')
    op.drop_column('event_participants', 'code_of_conduct_confirm')
    op.drop_column('event_participants', 'motivation_letter')
    op.drop_column('event_participants', 'badge_name')
    op.drop_column('event_participants', 'certificate_name')
    op.drop_column('event_participants', 'daily_meals')
    op.drop_column('event_participants', 'accommodation_needs')
    op.drop_column('event_participants', 'travelling_internationally')
    op.drop_column('event_participants', 'phone_number')
    op.drop_column('event_participants', 'line_manager_email')
    op.drop_column('event_participants', 'ld_manager_email')
    op.drop_column('event_participants', 'career_manager_email')
    op.drop_column('event_participants', 'hrco_email')
    op.drop_column('event_participants', 'msf_email')
    op.drop_column('event_participants', 'personal_email')
    op.drop_column('event_participants', 'project_of_work')
    op.drop_column('event_participants', 'country_of_work')
    op.drop_column('event_participants', 'current_position')
    op.drop_column('event_participants', 'pronouns')
    op.drop_column('event_participants', 'sex')
    op.drop_column('event_participants', 'gender_identity')
    op.drop_column('event_participants', 'contract_type')
    op.drop_column('event_participants', 'contract_status')
    op.drop_column('event_participants', 'oc')
    op.drop_column('event_participants', 'last_name')
    op.drop_column('event_participants', 'first_name')