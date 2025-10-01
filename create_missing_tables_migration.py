#!/usr/bin/env python3
"""
Create missing tables migration
"""
import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from alembic import command
from alembic.config import Config

def create_migration():
    """Create migration for missing tables"""
    
    # Create the migration
    alembic_cfg = Config("alembic.ini")
    command.revision(alembic_cfg, message="Create user_roles and admin_invitations tables", autogenerate=True)
    print("✅ Migration created successfully!")
    print("Run 'alembic upgrade head' to apply the migration")

if __name__ == "__main__":
    create_migration()