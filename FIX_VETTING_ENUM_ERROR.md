# Fix for Vetting Committee Enum Error

## Problem
When editing the vetting committee, you get this error:
```
sqlalchemy.exc.StatementError: (builtins.LookupError) 'UserRole.VETTING_APPROVER' is not among the defined enum values. Enum name: roletype. Possible values: SUPER_ADMIN, MT_ADMIN, HR_ADMIN, ..., STAFF
```

## Root Cause
The database enum type `roletype` is missing the `VETTING_APPROVER` and `VETTING_COMMITTEE` values that are defined in the Python code.

## Solution

### Option 1: Run the SQL Script Directly (FASTEST)

1. Connect to your PostgreSQL database on the server:
```bash
sudo -u postgres psql -d msafiri_db
```

2. Run the fix script:
```bash
\i /home/leo-server/projects/msafiri/msafiri-visitor-api/fix_vetting_enum.sql
```

Or copy and paste the SQL directly:
```sql
-- Add VETTING_APPROVER if it doesn't exist
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_enum 
        WHERE enumlabel = 'VETTING_APPROVER' 
        AND enumtypid = (SELECT oid FROM pg_type WHERE typname = 'roletype')
    ) THEN
        ALTER TYPE roletype ADD VALUE 'VETTING_APPROVER';
    END IF;
END$$;

-- Add VETTING_COMMITTEE if it doesn't exist
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_enum 
        WHERE enumlabel = 'VETTING_COMMITTEE' 
        AND enumtypid = (SELECT oid FROM pg_type WHERE typname = 'roletype')
    ) THEN
        ALTER TYPE roletype ADD VALUE 'VETTING_COMMITTEE';
    END IF;
END$$;
```

3. Verify the fix:
```sql
SELECT enumlabel 
FROM pg_enum 
WHERE enumtypid = (SELECT oid FROM pg_type WHERE typname = 'roletype')
ORDER BY enumsortorder;
```

You should see `VETTING_APPROVER` and `VETTING_COMMITTEE` in the list.

4. Exit psql:
```
\q
```

5. Restart the API service:
```bash
sudo systemctl restart msafiri-api
```

### Option 2: Run Alembic Migration

1. SSH into the server
2. Navigate to the API directory:
```bash
cd /home/leo-server/projects/msafiri/msafiri-visitor-api
```

3. Activate the virtual environment:
```bash
source venv/bin/activate
```

4. Run the migration:
```bash
alembic upgrade head
```

5. Restart the API service:
```bash
sudo systemctl restart msafiri-api
```

## Verification

After applying the fix, try editing the vetting committee again at:
http://localhost:3000/tenant/oca-kenya/events/23/vetting-committee

The error should be resolved.

## Files Changed
- `alembic/versions/101_ensure_vetting_roles_in_enum.py` - New migration file
- `fix_vetting_enum.sql` - SQL script for direct database fix
- `FIX_VETTING_ENUM_ERROR.md` - This documentation file
