#!/usr/bin/env python3
import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

try:
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()
    
    with open('fix_vendor_accommodations_table.sql', 'r') as f:
        sql = f.read()
    
    cur.execute(sql)
    conn.commit()
    print("Vendor accommodations table columns added successfully!")
    
except Exception as e:
    print(f"Error: {e}")
finally:
    if 'cur' in locals():
        cur.close()
    if 'conn' in locals():
        conn.close()