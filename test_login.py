#!/usr/bin/env python3

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.core.config import settings
from app.models.user import User

def test_user_query():
    """Test that we can query users without relationship errors"""
    
    engine = create_engine(settings.DATABASE_URL)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    
    try:
        db = SessionLocal()
        
        # Test basic user query
        users = db.query(User).limit(5).all()
        print(f"Successfully queried {len(users)} users")
        
        if users:
            user = users[0]
            print(f"Sample user: {user.email}, Role: {user.role}")
        
        db.close()
        print("User queries working correctly!")
        
    except Exception as e:
        print(f"Error querying users: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_user_query()