"""change registration_deadline to timestamp

Revision ID: change_reg_deadline_timestamp
Revises: 
Create Date: 2024-12-19 08:30:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'change_reg_deadline_timestamp'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    """Change registration_deadline from DATE to TIMESTAMP WITH TIME ZONE"""
    # First, add a new temporary column
    op.add_column('events', sa.Column('registration_deadline_temp', sa.DateTime(timezone=True), nullable=True))
    
    # Copy data from old column to new column, setting time to 09:00:00
    op.execute("""
        UPDATE events 
        SET registration_deadline_temp = registration_deadline + INTERVAL '9 hours'
        WHERE registration_deadline IS NOT NULL
    """)
    
    # Drop the old column
    op.drop_column('events', 'registration_deadline')
    
    # Rename the new column
    op.alter_column('events', 'registration_deadline_temp', new_column_name='registration_deadline')


def downgrade():
    """Change registration_deadline back from TIMESTAMP to DATE"""
    # Add temporary date column
    op.add_column('events', sa.Column('registration_deadline_temp', sa.Date(), nullable=True))
    
    # Copy data, extracting just the date part
    op.execute("""
        UPDATE events 
        SET registration_deadline_temp = registration_deadline::date
        WHERE registration_deadline IS NOT NULL
    """)
    
    # Drop the timestamp column
    op.drop_column('events', 'registration_deadline')
    
    # Rename the temp column back
    op.alter_column('events', 'registration_deadline_temp', new_column_name='registration_deadline')