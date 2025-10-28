-- Add is_read column to direct_messages table

-- Check if column exists
SELECT 'Checking if is_read column exists...' as info;
SELECT column_name 
FROM information_schema.columns 
WHERE table_name = 'direct_messages' 
AND column_name = 'is_read';

-- Add the column if it doesn't exist
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'direct_messages' 
        AND column_name = 'is_read'
    ) THEN
        ALTER TABLE direct_messages ADD COLUMN is_read BOOLEAN DEFAULT FALSE;
        RAISE NOTICE 'Added is_read column to direct_messages table';
    ELSE
        RAISE NOTICE 'is_read column already exists in direct_messages table';
    END IF;
END$$;

-- Verify the column was added
SELECT 'Final verification:' as info;
SELECT column_name, data_type, column_default
FROM information_schema.columns 
WHERE table_name = 'direct_messages' 
AND column_name = 'is_read';