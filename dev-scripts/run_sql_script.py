#!/usr/bin/env python3
import os
import psycopg2
from psycopg2 import sql

# Database connection parameters
DB_CONFIG = {
    'host': 'localhost',
    'database': 'msafiri_db',
    'user': 'postgres',
    'password': 'admin',
    'port': 5432
}

def run_sql_file(filename):
    try:
        # Connect to database
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        # Read and execute SQL file
        with open(filename, 'r') as file:
            sql_commands = file.read()
            cursor.execute(sql_commands)
        
        conn.commit()
        cursor.close()
        conn.close()
        
        print(f"Successfully executed {filename}")
        return True
        
    except Exception as e:
        print(f"Error executing {filename}: {e}")
        return False

if __name__ == "__main__":
    success = run_sql_file("create_invitations_table.sql")
    if success:
        print("Invitations table created successfully!")
    else:
        print("Failed to create invitations table")