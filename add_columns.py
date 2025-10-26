from app.db.database import engine
from sqlalchemy import text

with engine.connect() as conn:
    try:
        conn.execute(text("""
            ALTER TABLE guesthouses 
            ADD COLUMN IF NOT EXISTS contact_person VARCHAR(200),
            ADD COLUMN IF NOT EXISTS phone VARCHAR(20),
            ADD COLUMN IF NOT EXISTS email VARCHAR(100),
            ADD COLUMN IF NOT EXISTS facilities TEXT,
            ADD COLUMN IF NOT EXISTS house_rules TEXT,
            ADD COLUMN IF NOT EXISTS check_in_time VARCHAR(10),
            ADD COLUMN IF NOT EXISTS check_out_time VARCHAR(10)
        """))
        conn.commit()
        print("Columns added successfully")
    except Exception as e:
        print(f"Error: {e}")