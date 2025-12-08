# Database Migration Instructions

## Line Manager Recommendation - Text to Checkbox Migration

### What Changed
- Changed line manager recommendation from text field to simple checkbox
- Database field changed from `recommendation_text` (TEXT) to `is_recommended` (BOOLEAN)
- Line managers now just check a box to recommend instead of writing text

### Running the Migration on Server

#### Step 1: SSH into the server
```bash
ssh leo-server@41.90.97.253
```

#### Step 2: Navigate to the API directory
```bash
cd ~/projects/msafiri/msafiri-visitor-api
```

#### Step 3: Pull the latest changes
```bash
git pull origin master
```

#### Step 4: Activate the virtual environment
```bash
source venv/bin/activate
```

#### Step 5: Run the migration
```bash
alembic upgrade head
```

#### Step 6: Restart the API service
```bash
sudo systemctl restart msafiri-api
```

#### Step 7: Check the service status
```bash
sudo systemctl status msafiri-api
```

#### Step 8: Check the logs (if needed)
```bash
sudo journalctl -u msafiri-api -f
```

### Verification
After running the migration, you can verify it worked by:
1. Checking that the API starts without errors
2. Testing the line manager recommendation endpoint
3. Verifying existing recommendations were migrated (submitted ones should have `is_recommended = TRUE`)

### Rollback (if needed)
If something goes wrong, you can rollback the migration:
```bash
alembic downgrade -1
```

This will revert the `is_recommended` boolean back to `recommendation_text` text field.

### Migration Details
- **Migration File**: `alembic/versions/change_recommendation_to_boolean.py`
- **Revision ID**: `change_recommendation_to_boolean`
- **Previous Revision**: `fix_tenant_id_type_mismatch`

### What the Migration Does
1. Drops the `recommendation_text` column (TEXT type)
2. Adds `is_recommended` column (BOOLEAN type, default FALSE)
3. Updates existing records: sets `is_recommended = TRUE` where `submitted_at IS NOT NULL`
4. Makes `is_recommended` NOT NULL with server default FALSE
