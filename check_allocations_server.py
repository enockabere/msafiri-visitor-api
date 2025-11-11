#!/usr/bin/env python3
"""
Server script to check existing allocations and participants
Run this on the server to debug allocation issues
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import create_engine, text
from app.core.config import settings

def check_allocations():
    """Check existing allocations and participants"""
    
    print(f"Connecting to database: {settings.DATABASE_URL}")
    engine = create_engine(settings.DATABASE_URL)
    
    try:
        with engine.connect() as connection:
            # Check event participants
            result = connection.execute(text("""
                SELECT id, email, full_name, event_id 
                FROM event_participants 
                WHERE email = 'kenya-visitor@oca.msf.org'
                ORDER BY id
            """))
            
            participants = result.fetchall()
            print(f"\n👥 Found {len(participants)} participants for kenya-visitor@oca.msf.org:")
            for p in participants:
                print(f"  ID: {p[0]}, Email: {p[1]}, Name: {p[2]}, Event: {p[3]}")
            
            if not participants:
                print("❌ No participants found for kenya-visitor@oca.msf.org")
                return
            
            # Check events for these participants
            event_ids = [str(p[3]) for p in participants]
            if event_ids:
                result = connection.execute(text(f"""
                    SELECT id, title, location, status 
                    FROM events 
                    WHERE id IN ({','.join(event_ids)})
                """))
                
                events = result.fetchall()
                print(f"\n🎯 Events for these participants:")
                for e in events:
                    print(f"  ID: {e[0]}, Title: {e[1]}, Location: {e[2]}, Status: {e[3]}")
            
            # Check event allocations
            result = connection.execute(text(f"""
                SELECT id, event_id, drink_vouchers_per_participant, status, created_at
                FROM event_allocations 
                WHERE event_id IN ({','.join(event_ids)})
                AND drink_vouchers_per_participant > 0
                ORDER BY event_id, id
            """))
            
            allocations = result.fetchall()
            print(f"\n🎫 Found {len(allocations)} voucher allocations:")
            for a in allocations:
                print(f"  ID: {a[0]}, Event: {a[1]}, Vouchers: {a[2]}, Status: {a[3]}, Created: {a[4]}")
            
            if not allocations:
                print("❌ No voucher allocations found for these events")
                
                # Check if there are any allocations at all
                result = connection.execute(text("""
                    SELECT COUNT(*) FROM event_allocations
                """))
                total_allocations = result.fetchone()[0]
                print(f"📊 Total allocations in database: {total_allocations}")
                
                if total_allocations > 0:
                    result = connection.execute(text("""
                        SELECT id, event_id, drink_vouchers_per_participant 
                        FROM event_allocations 
                        WHERE drink_vouchers_per_participant > 0
                        LIMIT 5
                    """))
                    sample_allocations = result.fetchall()
                    print(f"📋 Sample voucher allocations:")
                    for sa in sample_allocations:
                        print(f"  ID: {sa[0]}, Event: {sa[1]}, Vouchers: {sa[2]}")
            
            # Check if participant_voucher_redemptions table exists
            result = connection.execute(text("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_name = 'participant_voucher_redemptions'
            """))
            
            if result.fetchone():
                print("\n✅ participant_voucher_redemptions table exists")
                
                # Check redemptions
                result = connection.execute(text("""
                    SELECT COUNT(*) FROM participant_voucher_redemptions
                """))
                redemption_count = result.fetchone()[0]
                print(f"📊 Total redemptions: {redemption_count}")
            else:
                print("\n❌ participant_voucher_redemptions table does NOT exist")
                print("🔧 Run create_voucher_table_server.py to create it")
                
    except Exception as e:
        print(f"❌ Error checking allocations: {e}")
        import traceback
        print(f"📋 Traceback: {traceback.format_exc()}")

if __name__ == "__main__":
    print("🔍 Checking allocations and participants...")
    check_allocations()