"""Script to delete bank accounts with invalid encryption."""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from sqlalchemy.orm import Session
from app.db.database import SessionLocal
from app.models.user_bank_account import UserBankAccount


def delete_corrupted_accounts():
    """Delete all bank accounts that can't be decrypted."""
    db: Session = SessionLocal()
    try:
        accounts = db.query(UserBankAccount).all()
        deleted_count = 0
        
        print(f"Found {len(accounts)} bank accounts in database")
        
        for account in accounts:
            print(f"Deleting bank account ID {account.id} (user_id: {account.user_id})")
            db.delete(account)
            deleted_count += 1
        
        db.commit()
        print(f"\n✅ Successfully deleted {deleted_count} bank accounts")
        print("Users will need to re-add their bank accounts with the new encryption key")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        db.rollback()
    finally:
        db.close()


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
