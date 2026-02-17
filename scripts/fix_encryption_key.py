"""Script to delete bank accounts with invalid encryption."""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from sqlalchemy import create_engine, text
from app.core.config import settings


def delete_corrupted_accounts():
    """Delete all bank accounts that can't be decrypted."""
    engine = create_engine(settings.DATABASE_URL)
    try:
        with engine.connect() as conn:
            result = conn.execute(text("SELECT COUNT(*) FROM user_bank_accounts"))
            count = result.scalar()
            print(f"Found {count} bank accounts in database")
            
            conn.execute(text("DELETE FROM user_bank_accounts"))
            conn.commit()
            
            print(f"\n✅ Successfully deleted {count} bank accounts")
            print("Users will need to re-add their bank accounts with the new encryption key")
        
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        engine.dispose()


if __name__ == "__main__":
    print("=" * 60)
    print("BANK ACCOUNT ENCRYPTION FIX")
    print("=" * 60)
    print("\nThis script will DELETE all existing bank accounts.")
    print("Users will need to re-add their bank accounts.")
    print("\nMake sure you have:")
    print("1. Set a new ENCRYPTION_KEY in your .env file")
    print("2. Restarted the API server")
    print("\n" + "=" * 60)
    
    response = input("\nDo you want to continue? (yes/no): ")
    if response.lower() == 'yes':
        delete_corrupted_accounts()
    else:
        print("Operation cancelled")
