"""Change registration_deadline to datetime

Revision ID: f1a2b3c4d5e6
Revises: 
Create Date: 2024-12-19 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'f1a2b3c4d5e6'
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    # Change registration_deadline from date to datetime
    # First add a new datetime column
    op.add_column('events', sa.Column('registration_deadline_temp', sa.DateTime(), nullable=True))
    
    # Copy data from old column to new column (set time to 00:00:00)
    op.execute("UPDATE events SET registration_deadline_temp = registration_deadline::timestamp")
    
    # Drop old column
    op.drop_column('events', 'registration_deadline')
    
    # Rename new column to original name
    op.alter_column('events', 'registration_deadline_temp', new_column_name='registration_deadline')
    
    # Make it not nullable
    op.alter_column('events', 'registration_deadline', nullable=False)

def downgrade():
    # Change registration_deadline from datetime back to date
    op.add_column('events', sa.Column('registration_deadline_temp', sa.Date(), nullable=True))
    op.execute("UPDATE events SET registration_deadline_temp = registration_deadline::date")
    op.drop_column('events', 'registration_deadline')
    op.alter_column('events', 'registration_deadline_temp', new_column_name='registration_deadline')
    op.alter_column('events', 'registration_deadline', nullable=False)