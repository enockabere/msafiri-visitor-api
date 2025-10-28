-- Fix news category enum by removing 'security' category
-- Run this SQL script on the deployed database

BEGIN;

-- Check current enum values
SELECT 'Current enum values:' as info;
SELECT unnest(enum_range(NULL::newscategory)) as current_values;

-- Update the enum type
ALTER TYPE newscategory RENAME TO newscategory_old;
CREATE TYPE newscategory AS ENUM ('health_program', 'security_briefing', 'events', 'reports', 'general', 'announcement');
ALTER TABLE news_updates ALTER COLUMN category TYPE newscategory USING category::text::newscategory;
DROP TYPE newscategory_old;

-- Verify the change
SELECT 'New enum values:' as info;
SELECT unnest(enum_range(NULL::newscategory)) as new_values;

COMMIT;

-- Success message
SELECT 'News category enum updated successfully!' as result;