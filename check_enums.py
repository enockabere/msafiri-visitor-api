#!/usr/bin/env python3
import sys
sys.path.append('.')

from sqlalchemy import text
from app.db.database import engine

def check_enum_values():
    """Check current enum values in database"""
    
    try:
        with engine.connect() as conn:
            # Check paymentmethod enum values
            result = conn.execute(text("""
                SELECT enumlabel 
                FROM pg_enum 
                WHERE enumtypid = (
                    SELECT oid 
                    FROM pg_type 
                    WHERE typname = 'paymentmethod'
                )
                ORDER BY enumsortorder
            """))
            
            payment_values = [row[0] for row in result.fetchall()]
            print(f"PaymentMethod enum values in database: {payment_values}")
            
            # Check cashhours enum values
            result = conn.execute(text("""
                SELECT enumlabel 
                FROM pg_enum 
                WHERE enumtypid = (
                    SELECT oid 
                    FROM pg_type 
                    WHERE typname = 'cashhours'
                )
                ORDER BY enumsortorder
            """))
            
            cash_hours_values = [row[0] for row in result.fetchall()]
            print(f"CashHours enum values in database: {cash_hours_values}")
            
    except Exception as e:
        print(f"Error checking enum values: {e}")

if __name__ == "__main__":
    check_enum_values()