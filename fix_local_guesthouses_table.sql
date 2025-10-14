-- Add missing columns to guesthouses table in local database
ALTER TABLE guesthouses ADD COLUMN IF NOT EXISTS latitude NUMERIC(10,8);
ALTER TABLE guesthouses ADD COLUMN IF NOT EXISTS longitude NUMERIC(11,8);