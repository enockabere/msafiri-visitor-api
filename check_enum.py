import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

# Connect to database
conn = psycopg2.connect(
    host=os.getenv("DATABASE_HOST"),
    database=os.getenv("DATABASE_NAME"),
    user=os.getenv("DATABASE_USER"),
    password=os.getenv("DATABASE_PASSWORD"),
    port=os.getenv("DATABASE_PORT", 5432)
)

cur = conn.cursor()

# Check enum values
cur.execute("SELECT unnest(enum_range(NULL::newscategory))")
enum_values = cur.fetchall()
print("Current enum values:")
for val in enum_values:
    print(f"  {val[0]}")

# Check actual data in table
cur.execute("SELECT DISTINCT category FROM news_updates")
data_values = cur.fetchall()
print("\nActual values in table:")
for val in data_values:
    print(f"  {val[0]}")

cur.close()
conn.close()