#!/usr/bin/env python3
"""
Fix empty domain strings in tenants table
Converts empty strings to NULL to avoid unique constraint violations
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.orm import Session
from sqlalchemy import text
from app.db.database import SessionLocal

def fix_empty_domains():
    """Convert empty domain strings to NULL"""
    db: Session = SessionLocal()
    try:
        # Check how many tenants have empty domain strings
        result = db.execute(text("SELECT COUNT(*) FROM tenants WHERE domain = ''"))
        count = result.scalar()
        
        print(f"Found {count} tenants with empty domain strings")
        
        if count > 0:
            # Update empty domains to NULL
            result = db.execute(text("UPDATE tenants SET domain = NULL WHERE domain = ''"))
            print(f"Updated {result.rowcount} tenants")
            
            # Commit changes
            db.commit()
            print("Successfully updated empty domains to NULL")
        else:
            print("No empty domains found")
        
    except Exception as e:
        print(f"Error: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    fix_empty_domains()