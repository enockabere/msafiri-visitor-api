-- Fix enum values in news_updates table
-- Convert uppercase values to lowercase to match the model

-- First, update any existing data
UPDATE news_updates SET category = 'health_program' WHERE category = 'HEALTH_PROGRAM';
UPDATE news_updates SET category = 'security_briefing' WHERE category = 'SECURITY_BRIEFING';
UPDATE news_updates SET category = 'events' WHERE category = 'EVENTS';
UPDATE news_updates SET category = 'reports' WHERE category = 'REPORTS';
UPDATE news_updates SET category = 'general' WHERE category = 'GENERAL';
UPDATE news_updates SET category = 'announcement' WHERE category = 'ANNOUNCEMENT';

-- Drop and recreate the enum type with correct values
ALTER TABLE news_updates ALTER COLUMN category TYPE varchar(50);
DROP TYPE IF EXISTS newscategory;
CREATE TYPE newscategory AS ENUM ('health_program', 'security_briefing', 'events', 'reports', 'general', 'announcement');
ALTER TABLE news_updates ALTER COLUMN category TYPE newscategory USING category::newscategory;