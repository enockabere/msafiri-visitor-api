#!/usr/bin/env python3

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy.orm import Session
from app.db.database import SessionLocal
from app.models.user import User, UserRole
from app.models.tenant import Tenant
from app.core.tenant_auto_assignment import auto_assign_tenant_admin

def test_scenario():
    db: Session = SessionLocal()
    try:
        # Find a user to test with
        user = db.query(User).filter(User.email == "maebaenock95@gmail.com").first()
        if user:
            print(f"Testing with user: {user.email}")
            print(f"Current tenant_id: {user.tenant_id}")
            
            # Temporarily remove tenant_id to test auto-assignment
            original_tenant_id = user.tenant_id
            user.tenant_id = None
            db.commit()
            print(f"Removed tenant_id, now: {user.tenant_id}")
            
            # Test auto-assignment
            result = auto_assign_tenant_admin(db, user)
            print(f"Auto-assignment result: {result}")
            
            # Check final state
            db.refresh(user)
            print(f"Final tenant_id: {user.tenant_id}")
            
            # Restore original state if needed
            if not user.tenant_id:
                user.tenant_id = original_tenant_id
                db.commit()
                print(f"Restored original tenant_id: {user.tenant_id}")
        else:
            print("Test user not found")
            
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    test_scenario()