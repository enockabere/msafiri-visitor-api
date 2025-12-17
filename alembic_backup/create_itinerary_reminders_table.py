"""create itinerary reminders table

Revision ID: create_itinerary_reminders
Revises: f1895cdab0c6
Create Date: 2024-11-05 16:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql import func

# revision identifiers, used by Alembic.
revision = 'create_itinerary_reminders'
down_revision = 'create_event_voucher_scanners'
branch_labels = None
depends_on = None

def upgrade():
    op.create_table(
        'itinerary_reminders',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('event_id', sa.Integer(), nullable=False),
        sa.Column('user_email', sa.String(), nullable=False),
        sa.Column('reminder_date', sa.DateTime(), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=func.now(), nullable=True),
        sa.Column('is_active', sa.Boolean(), default=True, nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_itinerary_reminders_id', 'itinerary_reminders', ['id'])
    op.create_index('ix_itinerary_reminders_event_id', 'itinerary_reminders', ['event_id'])
    op.create_index('ix_itinerary_reminders_user_email', 'itinerary_reminders', ['user_email'])

def downgrade():
    op.drop_index('ix_itinerary_reminders_user_email', table_name='itinerary_reminders')
    op.drop_index('ix_itinerary_reminders_event_id', table_name='itinerary_reminders')
    op.drop_index('ix_itinerary_reminders_id', table_name='itinerary_reminders')
    op.drop_table('itinerary_reminders')