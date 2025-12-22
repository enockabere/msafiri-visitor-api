-- Fix registration_deadline column to be datetime instead of date
-- This allows storing both date and time for registration deadlines

-- Step 1: Add a temporary datetime column
ALTER TABLE events ADD COLUMN registration_deadline_temp TIMESTAMP;

-- Step 2: Copy existing date data to the new column (set time to 00:00:00)
UPDATE events SET registration_deadline_temp = registration_deadline::timestamp;

-- Step 3: Drop the old date column
ALTER TABLE events DROP COLUMN registration_deadline;

-- Step 4: Rename the new column to the original name
ALTER TABLE events RENAME COLUMN registration_deadline_temp TO registration_deadline;

-- Step 5: Make it NOT NULL (if needed)
ALTER TABLE events ALTER COLUMN registration_deadline SET NOT NULL;