# Fix Missing Tables on Server

## Problem
The public registration page is failing because two tables are missing from the database:
1. `public_registrations` - stores detailed registration information
2. `line_manager_recommendations` - stores line manager recommendation requests

## Solution

### Option 1: Run SQL Script Directly (Recommended)

**On the server, run:**

```bash
# Connect to PostgreSQL
psql -U your_database_user -d your_database_name -f create_registration_tables.sql
```

**Or if using a different user:**

```bash
sudo -u postgres psql -d msafiri_db -f create_registration_tables.sql
```

### Option 2: Run via Python Shell

```bash
# Activate your virtual environment
cd /path/to/msafiri-visitor-api
source venv/bin/activate  # or ./venv/Scripts/activate on Windows

# Run Python shell
python
```

Then in the Python shell:

```python
from app.db.database import engine
from sqlalchemy import text

# Read the SQL file
with open('create_registration_tables.sql', 'r') as f:
    sql = f.read()

# Execute the SQL
with engine.connect() as conn:
    conn.execute(text(sql))
    conn.commit()

print("✅ Tables created successfully!")
```

### Option 3: Connect Directly to Database

```bash
# If you have direct database access
psql postgresql://username:password@host:port/database

# Then paste the contents of create_registration_tables.sql
```

## Verification

After running the script, verify the tables were created:

```sql
-- Check if tables exist
SELECT table_name FROM information_schema.tables
WHERE table_name IN ('public_registrations', 'line_manager_recommendations');

-- Check columns in public_registrations
SELECT column_name, data_type
FROM information_schema.columns
WHERE table_name = 'public_registrations'
ORDER BY ordinal_position;

-- Check columns in line_manager_recommendations
SELECT column_name, data_type
FROM information_schema.columns
WHERE table_name = 'line_manager_recommendations'
ORDER BY ordinal_position;
```

## What These Tables Do

### public_registrations
Stores detailed registration information from the public registration form including:
- Personal information (name, emails, phone)
- Work information (OC, position, contract type)
- Travel details (international travel, accommodation preferences)
- Dietary and accommodation requirements
- Certificate and badge names
- Motivation letter
- Confirmations (code of conduct, travel requirements)

### line_manager_recommendations
Stores line manager recommendation requests including:
- Link between registration and event
- Participant and line manager information
- Unique recommendation token for secure access
- Recommendation status and decision
- Recommendation text from line manager

## Files Created

- `create_registration_tables.sql` - Complete SQL script to create both tables
- `FIX_MISSING_TABLES.md` - This file with instructions

## Next Steps

1. Run the SQL script on the production server
2. Test the public registration page: `http://41.90.97.253:8001/public/event-registration/5`
3. Verify registrations are being saved correctly
4. Check that no more 404 table errors appear

## Troubleshooting

### Error: "permission denied for table"
You need to grant permissions to your database user:
```sql
GRANT ALL PRIVILEGES ON TABLE public_registrations TO your_user;
GRANT ALL PRIVILEGES ON TABLE line_manager_recommendations TO your_user;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO your_user;
```

### Error: "relation events does not exist"
Make sure your main tables (events, event_participants) exist first.

### Error: "column already exists"
The script uses `IF NOT EXISTS` and `DO $$` blocks to handle existing structures safely. You can run it multiple times.
