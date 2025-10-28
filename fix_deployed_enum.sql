-- Fix for deployed database enum issue
-- Run this on the server database

-- First check what enum values exist
SELECT unnest(enum_range(NULL::newscategory)) as enum_values;

-- Check what data exists in the table
SELECT DISTINCT category FROM news_updates;

-- Convert the enum column to varchar temporarily
ALTER TABLE news_updates ALTER COLUMN category TYPE varchar(50);

-- Drop the old enum type
DROP TYPE IF EXISTS newscategory;

-- Create new enum with lowercase values
CREATE TYPE newscategory AS ENUM ('health_program', 'security_briefing', 'events', 'reports', 'general', 'announcement');

-- Update any uppercase data to lowercase (if it exists)
UPDATE news_updates SET category = 'health_program' WHERE category = 'HEALTH_PROGRAM';
UPDATE news_updates SET category = 'security_briefing' WHERE category = 'SECURITY_BRIEFING';  
UPDATE news_updates SET category = 'events' WHERE category = 'EVENTS';
UPDATE news_updates SET category = 'reports' WHERE category = 'REPORTS';
UPDATE news_updates SET category = 'general' WHERE category = 'GENERAL';
UPDATE news_updates SET category = 'announcement' WHERE category = 'ANNOUNCEMENT';

-- Convert column back to enum type
ALTER TABLE news_updates ALTER COLUMN category TYPE newscategory USING category::newscategory;

-- Verify the fix
SELECT unnest(enum_range(NULL::newscategory)) as fixed_enum_values;
SELECT DISTINCT category FROM news_updates;