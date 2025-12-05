#!/usr/bin/env python3

import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Create a new migration file with correct parent revision
migration_content = '''"""Remove description column from guesthouses

Revision ID: remove_description_guesthouses_fix
Revises: simple_add_app_feedback_enum
Create Date: 2024-12-19 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'remove_description_guesthouses_fix'
down_revision = 'simple_add_app_feedback_enum'
branch_labels = None
depends_on = None


def upgrade():
    # Remove description column from guesthouses table
    op.drop_column('guesthouses', 'description')


def downgrade():
    # Add description column back to guesthouses table
    op.add_column('guesthouses', sa.Column('description', sa.Text(), nullable=True))
'''

# Write the new migration file
with open('alembic/versions/remove_description_guesthouses_fix.py', 'w') as f:
    f.write(migration_content)

print("Created new migration file: remove_description_guesthouses_fix.py")