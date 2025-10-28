# Database Enum Fix Instructions

## Problem
The database enum `newscategory` has uppercase values but the application expects lowercase values, causing this error:
```
'health_program' is not among the defined enum values. Enum name: newscategory. Possible values: HEALTH_PROG.., SECURITY_BR.., EVENTS, ..., ANNOUNCEMEN..
```

## Solution
Run the SQL script on the deployed database to fix the enum values.

## Steps to Fix

1. **Connect to the deployed PostgreSQL database**
   ```bash
   sudo -u postgres psql msafiri_db
   ```

2. **Run the fix script**
   ```bash
   \i /path/to/fix_deployed_enum.sql
   ```
   
   Or copy and paste the contents of `fix_deployed_enum.sql` into the psql prompt.

3. **Restart the API server**
   ```bash
   sudo systemctl restart gunicorn
   ```

## What the script does
1. Converts the enum column to varchar temporarily
2. Drops the old enum type with uppercase values
3. Creates new enum type with lowercase values
4. Updates any existing uppercase data to lowercase
5. Converts the column back to the enum type
6. Verifies the fix worked

## Verification
After running the script, the API should work without enum errors. Check the logs:
```bash
sudo journalctl -u gunicorn -f
```