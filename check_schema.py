from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

DATABASE_URL = "postgresql://postgres:admin@localhost:5432/msafiri_db"

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
db = SessionLocal()

# Check current table schema
result = db.execute(text("""
    SELECT column_name, data_type, is_nullable 
    FROM information_schema.columns 
    WHERE table_name = 'line_manager_recommendations' 
    ORDER BY ordinal_position
"""))

print("Current line_manager_recommendations table schema:")
for row in result:
    print(f"  {row[0]} - {row[1]} ({'NULL' if row[2] == 'YES' else 'NOT NULL'})")

db.close()