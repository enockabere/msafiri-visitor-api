# Server Migration Commands

Run these commands on your deployed server in the API directory:

## 1. Check current migration status
```bash
alembic current
```

## 2. Check available migrations
```bash
alembic heads
```

## 3. Run the migration to fix the enum
```bash
alembic upgrade head
```

## 4. If you get multiple heads error, merge them first:
```bash
alembic merge heads -m "merge_migration_heads"
alembic upgrade head
```

## Alternative: Run migration directly with Python
```bash
python -m alembic upgrade head
```

The migration file `61b460aa1b53_remove_security_category_from_news_enum.py` will:
- Remove the 'security' category from the news enum
- Keep only: health_program, security_briefing, events, reports, general, announcement