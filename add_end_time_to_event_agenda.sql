-- Add end_time column to event_agenda table
-- This allows storing both start and end times for agenda items

ALTER TABLE event_agenda
ADD COLUMN IF NOT EXISTS end_time VARCHAR(10);

-- Add a comment to the column
COMMENT ON COLUMN event_agenda.end_time IS 'End time of the agenda item in HH:MM format (e.g., "10:00", "15:30")';

-- Update existing records to have end_time same as start time + 1 hour as default
UPDATE event_agenda
SET end_time = (
    CASE
        WHEN CAST(SUBSTRING(time, 1, 2) AS INTEGER) < 23
        THEN LPAD((CAST(SUBSTRING(time, 1, 2) AS INTEGER) + 1)::TEXT, 2, '0') || SUBSTRING(time, 3, 3)
        ELSE '23:59'
    END
)
WHERE end_time IS NULL;

-- Verify the changes
SELECT id, title, time AS start_time, end_time
FROM event_agenda
ORDER BY event_date, time
LIMIT 10;
