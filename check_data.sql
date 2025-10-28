-- Check what's actually in the database
SELECT id, title, category FROM news_updates;

-- Check enum definition
SELECT unnest(enum_range(NULL::newscategory)) as enum_values;

-- Try to select with specific category
SELECT id, title, category FROM news_updates WHERE category = 'health_program';