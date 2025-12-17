#!/usr/bin/env python3
from sqlalchemy import text
from app.db.database import SessionLocal

db = SessionLocal()
try:
    result = db.execute(text('SELECT DISTINCT role FROM users'))
    roles = [r[0] for r in result.fetchall()]
    print('Current roles in database:', roles)
finally:
    db.close()