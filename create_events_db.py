import psycopg2
import os

# Database connection
conn = psycopg2.connect(
    host="localhost",
    database="msafiri_db",
    user="postgres",
    password="admin"
)

cur = conn.cursor()

# Read and execute SQL
with open('create_simple_events_table.sql', 'r') as f:
    sql = f.read()

cur.execute(sql)
conn.commit()

print("Events table created successfully!")

cur.close()
conn.close()