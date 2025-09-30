#!/usr/bin/env python3
import os
import sys
from alembic.config import Config
from alembic import command

# Set the database URL to use local database
os.environ['DATABASE_URL'] = 'postgresql://postgres:admin@localhost:5432/msafiri_db'

# Create alembic config
alembic_cfg = Config("alembic.ini")
alembic_cfg.set_main_option("sqlalchemy.url", os.environ['DATABASE_URL'])

try:
    # Run the specific migration to create invitations table
    command.upgrade(alembic_cfg, "create_invitations_table")
    print("Migration completed successfully!")
except Exception as e:
    print(f"Migration failed: {e}")
    sys.exit(1)