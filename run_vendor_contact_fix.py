#!/usr/bin/env python3
import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()
DATABASE_URL = os.getenv('DATABASE_URL')

def run_fix():
    engine = create_engine(DATABASE_URL)
    
    with open('fix_vendor_contact_constraint.sql', 'r') as f:
        sql_commands = f.read().split(';')
    
    with engine.connect() as conn:
        for cmd in sql_commands:
            if cmd.strip():
                conn.execute(text(cmd))
        conn.commit()
    
    print("Vendor accommodations contact constraints fixed successfully")

if __name__ == "__main__":
    run_fix()