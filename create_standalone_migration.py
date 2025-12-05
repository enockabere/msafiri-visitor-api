#!/usr/bin/env python3

import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Create a standalone migration file that can be run manually
migration_content = '''"""Remove description column from guesthouses - standalone

Revision ID: remove_description_standalone
Revises: 
Create Date: 2024-12-19 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'remove_description_standalone'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # Check if column exists before dropping it
    try:
        op.drop_column('guesthouses', 'description')
        print("Successfully removed description column from guesthouses table")
    except Exception as e:
        print(f"Column may not exist or already removed: {e}")


def downgrade():
    # Add description column back to guesthouses table
    op.add_column('guesthouses', sa.Column('description', sa.Text(), nullable=True))
'''

# Write the new migration file
with open('alembic/versions/remove_description_standalone.py', 'w') as f:
    f.write(migration_content)

print("Created standalone migration file: remove_description_standalone.py")