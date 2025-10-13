#!/usr/bin/env python3
import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()

# Use production database URL
DATABASE_URL = os.getenv("DATABASE_URL")

try:
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()
    
    with open('production_fix.sql', 'r') as f:
        sql = f.read()
    
    # Execute each statement separately
    statements = [stmt.strip() for stmt in sql.split(';') if stmt.strip() and not stmt.strip().startswith('--')]
    
    for statement in statements:
        if statement:
            print(f"Executing: {statement[:50]}...")
            cur.execute(statement)
    
    conn.commit()
    print("Production database fixes applied successfully!")
    
except Exception as e:
    print(f"Error: {e}")
    if 'conn' in locals():
        conn.rollback()
finally:
    if 'cur' in locals():
        cur.close()
    if 'conn' in locals():
        conn.close()