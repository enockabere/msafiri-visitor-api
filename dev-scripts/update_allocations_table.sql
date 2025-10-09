-- Update allocations table to support multiple items
ALTER TABLE event_allocations 
DROP COLUMN IF EXISTS inventory_item_id,
DROP COLUMN IF EXISTS quantity_per_participant,
ADD COLUMN IF NOT EXISTS items JSONB,
ADD COLUMN IF NOT EXISTS hr_notes TEXT,
ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;

-- Update existing records
UPDATE event_allocations 
SET items = '[]'::jsonb 
WHERE items IS NULL;

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_allocations_event_id ON event_allocations(event_id);
CREATE INDEX IF NOT EXISTS idx_allocations_status ON event_allocations(status);
CREATE INDEX IF NOT EXISTS idx_allocations_tenant_id ON event_allocations(tenant_id);
CREATE INDEX IF NOT EXISTS idx_allocations_items ON event_allocations USING GIN(items);