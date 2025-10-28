-- Fix notification enum to ensure APP_FEEDBACK value exists

-- Check current enum values
SELECT 'Current enum values:' as info;
SELECT enumlabel 
FROM pg_enum 
JOIN pg_type ON pg_enum.enumtypid = pg_type.oid 
WHERE pg_type.typname = 'notificationtype'
ORDER BY enumlabel;

-- Add APP_FEEDBACK if it doesn't exist (this will fail if it already exists, which is fine)
DO $$
BEGIN
    BEGIN
        ALTER TYPE notificationtype ADD VALUE 'APP_FEEDBACK';
        RAISE NOTICE 'Added APP_FEEDBACK to enum';
    EXCEPTION
        WHEN duplicate_object THEN
            RAISE NOTICE 'APP_FEEDBACK already exists in enum';
    END;
END$$;

-- Verify final state
SELECT 'Final enum values:' as info;
SELECT enumlabel 
FROM pg_enum 
JOIN pg_type ON pg_enum.enumtypid = pg_type.oid 
WHERE pg_type.typname = 'notificationtype'
ORDER BY enumlabel;