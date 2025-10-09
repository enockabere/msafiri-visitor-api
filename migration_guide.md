# Migration Best Practices

## Rules to Prevent Broken Migrations

### 1. Never Delete Migration Files
- Once committed, migration files are permanent
- Deleting them breaks the chain for other developers/servers

### 2. Always Use Sequential Workflow
```bash
# Correct workflow:
alembic revision --autogenerate -m "descriptive_message"
alembic upgrade head
git add alembic/versions/
git commit -m "Add migration: descriptive_message"
```

### 3. Never Edit Existing Migrations
- If you need to change something, create a new migration
- Use `alembic downgrade` then create new migration if needed

### 4. Sync Before Creating Migrations
```bash
git pull origin main
alembic upgrade head  # Ensure you're up to date
alembic revision --autogenerate -m "your_changes"
```

### 5. Test Migrations Before Committing
```bash
# Test the migration
alembic upgrade head
# Test rollback
alembic downgrade -1
alembic upgrade head
```

## Production Deployment

### Safe Migration Script
```bash
#!/bin/bash
# Always backup before migrations
pg_dump $DATABASE_URL > backup_$(date +%Y%m%d_%H%M%S).sql

# Run migrations
alembic upgrade head

# Restart server
systemctl restart msafiri-api
```

## Emergency Recovery

If migrations break:
1. Don't delete files
2. Use `alembic stamp head` to mark current state
3. Create new migration from current state
4. Never force-push migration changes