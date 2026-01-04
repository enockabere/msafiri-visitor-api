-- Create event_badges table
CREATE TABLE IF NOT EXISTS event_badges (
    id SERIAL PRIMARY KEY,
    event_id INTEGER NOT NULL,
    badge_template_id INTEGER NOT NULL,
    template_variables JSONB,
    tenant_id INTEGER NOT NULL,
    created_by VARCHAR(255) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    -- Foreign key constraints
    CONSTRAINT fk_event_badges_event_id 
        FOREIGN KEY (event_id) REFERENCES events(id) ON DELETE CASCADE,
    CONSTRAINT fk_event_badges_badge_template_id 
        FOREIGN KEY (badge_template_id) REFERENCES badge_templates(id) ON DELETE CASCADE,
    CONSTRAINT fk_event_badges_tenant_id 
        FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE
);

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_event_badges_event_id ON event_badges(event_id);
CREATE INDEX IF NOT EXISTS idx_event_badges_tenant_id ON event_badges(tenant_id);
CREATE INDEX IF NOT EXISTS idx_event_badges_template_id ON event_badges(badge_template_id);

-- Add updated_at trigger
CREATE OR REPLACE FUNCTION update_event_badges_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_event_badges_updated_at
    BEFORE UPDATE ON event_badges
    FOR EACH ROW
    EXECUTE FUNCTION update_event_badges_updated_at();