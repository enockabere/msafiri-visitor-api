import psycopg2

# Database connection
conn = psycopg2.connect(
    host="localhost",
    database="msafiri_db",
    user="postgres",
    password="admin"
)

cur = conn.cursor()

# Read and execute SQL
with open('add_event_columns.sql', 'r') as f:
    sql = f.read()

cur.execute(sql)
conn.commit()

print("Event columns added successfully!")

cur.close()
conn.close()