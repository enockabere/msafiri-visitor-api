-- Fix vetting_committees.tenant_id column type
-- Change from INTEGER to TEXT/VARCHAR to match the model

-- First, check current schema
SELECT column_name, data_type, is_nullable 
FROM information_schema.columns 
WHERE table_name = 'vetting_committees' 
AND column_name = 'tenant_id';

-- Update the column type from INTEGER to TEXT
ALTER TABLE vetting_committees 
ALTER COLUMN tenant_id TYPE TEXT;

-- Verify the change
SELECT column_name, data_type, is_nullable 
FROM information_schema.columns 
WHERE table_name = 'vetting_committees' 
AND column_name = 'tenant_id';