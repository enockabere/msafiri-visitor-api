import psycopg2

# Database connection
conn = psycopg2.connect(
    host="localhost",
    database="msafiri_db",
    user="postgres",
    password="admin"
)

cur = conn.cursor()

# Check what columns exist in events table
cur.execute("""
    SELECT column_name, data_type, is_nullable 
    FROM information_schema.columns 
    WHERE table_name = 'events'
    ORDER BY ordinal_position;
""")

columns = cur.fetchall()
print("Events table columns:")
for col in columns:
    print(f"  {col[0]} - {col[1]} - nullable: {col[2]}")

cur.close()
conn.close()