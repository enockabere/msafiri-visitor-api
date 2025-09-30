#!/usr/bin/env python3
"""
Add unique constraint to tenant name
"""
import sys
import os
sys.path.append('.')

from sqlalchemy import text
from app.db.database import engine

def add_unique_constraint():
    """Add unique constraint to tenant name"""
    try:
        with engine.connect() as conn:
            # Add unique constraint to tenant name
            conn.execute(text("""
                ALTER TABLE tenants 
                ADD CONSTRAINT unique_tenant_name UNIQUE (name)
            """))
            
            conn.commit()
            print("Unique constraint added to tenant name!")
            return True
            
    except Exception as e:
        if "already exists" in str(e):
            print("Unique constraint already exists")
            return True
        print(f"Error adding constraint: {e}")
        return False

if __name__ == "__main__":
    success = add_unique_constraint()
    sys.exit(0 if success else 1)