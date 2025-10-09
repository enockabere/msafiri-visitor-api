import psycopg2

# Database connection
conn = psycopg2.connect(
    host="localhost",
    database="msafiri_db",
    user="postgres",
    password="admin"
)

cur = conn.cursor()

# Check tenants table to find the ID for ko-oca
cur.execute("SELECT id, slug FROM tenants WHERE slug = 'ko-oca';")
tenant = cur.fetchone()
if tenant:
    print(f"Tenant ko-oca has ID: {tenant[0]}")
else:
    print("Tenant ko-oca not found")

# Also check all tenants
cur.execute("SELECT id, slug FROM tenants;")
tenants = cur.fetchall()
print("\nAll tenants:")
for t in tenants:
    print(f"  ID: {t[0]}, Slug: {t[1]}")

cur.close()
conn.close()