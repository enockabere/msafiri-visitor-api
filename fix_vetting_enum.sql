-- Fix for vetting committee enum error
-- This script adds the missing VETTING_APPROVER and VETTING_COMMITTEE values to the roletype enum

-- Add VETTING_APPROVER if it doesn't exist
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_enum 
        WHERE enumlabel = 'VETTING_APPROVER' 
        AND enumtypid = (SELECT oid FROM pg_type WHERE typname = 'roletype')
    ) THEN
        ALTER TYPE roletype ADD VALUE 'VETTING_APPROVER';
    END IF;
END$$;

-- Add VETTING_COMMITTEE if it doesn't exist
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_enum 
        WHERE enumlabel = 'VETTING_COMMITTEE' 
        AND enumtypid = (SELECT oid FROM pg_type WHERE typname = 'roletype')
    ) THEN
        ALTER TYPE roletype ADD VALUE 'VETTING_COMMITTEE';
    END IF;
END$$;

-- Verify the enum values
SELECT enumlabel 
FROM pg_enum 
WHERE enumtypid = (SELECT oid FROM pg_type WHERE typname = 'roletype')
ORDER BY enumsortorder;
