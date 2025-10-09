-- Add missing updated_at column to transport_status_updates table
ALTER TABLE transport_status_updates ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP WITH TIME ZONE;