#!/usr/bin/env python3
import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

try:
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()
    
    # Clear alembic version table
    cur.execute("DELETE FROM alembic_version;")
    
    # Set to a clean state - use the latest migration
    cur.execute("INSERT INTO alembic_version (version_num) VALUES ('add_missing_events_columns');")
    
    conn.commit()
    print("Alembic version table reset successfully!")
    
except Exception as e:
    print(f"Error: {e}")
    if 'conn' in locals():
        conn.rollback()
finally:
    if 'cur' in locals():
        cur.close()
    if 'conn' in locals():
        conn.close()