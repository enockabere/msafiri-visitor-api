from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

DATABASE_URL = "postgresql://postgres:admin@localhost:5432/msafiri_db"

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
db = SessionLocal()

print("=== CHECKING FORM RESPONSES TABLE ===")

# Check if form_responses table exists
table_exists = db.execute(text("""
    SELECT EXISTS (
        SELECT FROM information_schema.tables 
        WHERE table_schema = 'public' 
        AND table_name = 'form_responses'
    )
""")).scalar()

print(f"form_responses table exists: {table_exists}")

if table_exists:
    # Get all form responses
    responses = db.execute(text("""
        SELECT fr.*, ff.field_name, ff.field_label, ff.field_type
        FROM form_responses fr
        LEFT JOIN form_fields ff ON fr.field_id = ff.id
        ORDER BY fr.created_at DESC
        LIMIT 10
    """)).fetchall()
    
    print(f"Total form responses: {len(responses)}")
    for response in responses:
        print(f"Response: {dict(response._mapping)}")

# Check form_fields table
print("\n=== CHECKING FORM FIELDS TABLE ===")
fields = db.execute(text("""
    SELECT * FROM form_fields 
    WHERE event_id = 1
    ORDER BY order_index
""")).fetchall()

print(f"Form fields for event 1: {len(fields)}")
for field in fields:
    print(f"Field: {dict(field._mapping)}")

db.close()