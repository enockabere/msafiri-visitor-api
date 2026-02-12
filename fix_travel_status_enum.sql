-- Fix travel request status enum to accept both uppercase and lowercase values
-- Run this on the production database

-- Check current enum values
SELECT enumlabel FROM pg_enum WHERE enumtypid = 'travelrequeststatus'::regtype ORDER BY enumsortorder;

-- Option 1: Add uppercase values to the enum (if they don't exist)
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_enum WHERE enumlabel = 'DRAFT' AND enumtypid = 'travelrequeststatus'::regtype) THEN
        ALTER TYPE travelrequeststatus ADD VALUE 'DRAFT';
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_enum WHERE enumlabel = 'PENDING_APPROVAL' AND enumtypid = 'travelrequeststatus'::regtype) THEN
        ALTER TYPE travelrequeststatus ADD VALUE 'PENDING_APPROVAL';
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_enum WHERE enumlabel = 'APPROVED' AND enumtypid = 'travelrequeststatus'::regtype) THEN
        ALTER TYPE travelrequeststatus ADD VALUE 'APPROVED';
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_enum WHERE enumlabel = 'REJECTED' AND enumtypid = 'travelrequeststatus'::regtype) THEN
        ALTER TYPE travelrequeststatus ADD VALUE 'REJECTED';
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_enum WHERE enumlabel = 'COMPLETED' AND enumtypid = 'travelrequeststatus'::regtype) THEN
        ALTER TYPE travelrequeststatus ADD VALUE 'COMPLETED';
    END IF;
END$$;

-- Verify the enum now has both cases
SELECT enumlabel FROM pg_enum WHERE enumtypid = 'travelrequeststatus'::regtype ORDER BY enumsortorder;
