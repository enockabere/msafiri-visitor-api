from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

DATABASE_URL = "postgresql://postgres:admin@localhost:5432/msafiri_db"

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
db = SessionLocal()

try:
    # Check if contact_type column exists
    result = db.execute(text("""
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_name = 'line_manager_recommendations' 
        AND column_name = 'contact_type'
    """))
    
    if result.fetchone():
        print("contact_type column already exists")
    else:
        print("Adding contact_type column...")
        db.execute(text("""
            ALTER TABLE line_manager_recommendations 
            ADD COLUMN contact_type VARCHAR(50) DEFAULT 'Line Manager'
        """))
        db.commit()
        print("contact_type column added successfully")

except Exception as e:
    print(f"Error: {e}")
    db.rollback()
finally:
    db.close()