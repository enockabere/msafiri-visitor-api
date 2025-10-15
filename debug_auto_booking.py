#!/usr/bin/env python3
"""
Debug script to check auto booking system
"""
import sqlite3
import os

def check_database():
    """Check database for confirmed participants and allocations"""
    
    # Find the database file
    db_paths = [
        "app.db",
        "msafiri.db", 
        "database.db",
        "app/app.db"
    ]
    
    db_path = None
    for path in db_paths:
        if os.path.exists(path):
            db_path = path
            break
    
    if not db_path:
        print("❌ Database file not found")
        return
    
    print(f"📊 Using database: {db_path}")
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check confirmed participants
        print("\n🔍 Checking confirmed participants...")
        cursor.execute("""
            SELECT id, full_name, email, role, status, event_id 
            FROM event_participants 
            WHERE status = 'confirmed'
        """)
        confirmed_participants = cursor.fetchall()
        
        print(f"Found {len(confirmed_participants)} confirmed participants:")
        for p in confirmed_participants:
            print(f"  - ID: {p[0]}, Name: {p[1]}, Email: {p[2]}, Role: {p[3]}, Event: {p[5]}")
        
        # Check existing allocations
        print("\n🏨 Checking existing allocations...")
        cursor.execute("""
            SELECT id, guest_name, accommodation_type, status, participant_id, event_id
            FROM accommodation_allocations
        """)
        allocations = cursor.fetchall()
        
        print(f"Found {len(allocations)} allocations:")
        for a in allocations:
            print(f"  - ID: {a[0]}, Guest: {a[1]}, Type: {a[2]}, Status: {a[3]}, Participant: {a[4]}, Event: {a[5]}")
        
        # Check events with vendor accommodations
        print("\n🏢 Checking events with vendor accommodations...")
        cursor.execute("""
            SELECT id, title, vendor_accommodation_id, start_date, end_date
            FROM events
            WHERE vendor_accommodation_id IS NOT NULL
        """)
        events_with_vendors = cursor.fetchall()
        
        print(f"Found {len(events_with_vendors)} events with vendor accommodations:")
        for e in events_with_vendors:
            print(f"  - ID: {e[0]}, Title: {e[1]}, Vendor ID: {e[2]}")
        
        # Check vendor accommodations
        print("\n🏨 Checking vendor accommodations...")
        cursor.execute("""
            SELECT id, vendor_name, single_rooms, double_rooms
            FROM vendor_accommodations
        """)
        vendors = cursor.fetchall()
        
        print(f"Found {len(vendors)} vendor accommodations:")
        for v in vendors:
            print(f"  - ID: {v[0]}, Name: {v[1]}, Single: {v[2]}, Double: {v[3]}")
        
        conn.close()
        
    except Exception as e:
        print(f"💥 Error: {e}")

def check_tables():
    """Check if required tables exist"""
    
    db_paths = ["app.db", "msafiri.db", "database.db", "app/app.db"]
    
    db_path = None
    for path in db_paths:
        if os.path.exists(path):
            db_path = path
            break
    
    if not db_path:
        print("❌ Database file not found")
        return
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()
        
        print(f"📊 Found {len(tables)} tables:")
        required_tables = [
            'event_participants',
            'accommodation_allocations', 
            'vendor_accommodations',
            'events',
            'public_registrations'
        ]
        
        existing_tables = [t[0] for t in tables]
        
        for table in required_tables:
            if table in existing_tables:
                print(f"  ✅ {table}")
            else:
                print(f"  ❌ {table} (MISSING)")
        
        conn.close()
        
    except Exception as e:
        print(f"💥 Error: {e}")

if __name__ == "__main__":
    print("🔍 Auto Booking Debug Script")
    print("=" * 50)
    
    print("\n1. Checking database tables...")
    check_tables()
    
    print("\n2. Checking database data...")
    check_database()
    
    print("\n✅ Debug complete")