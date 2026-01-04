-- Create event_certificates table
CREATE TABLE IF NOT EXISTS event_certificates (
    id SERIAL PRIMARY KEY,
    event_id INTEGER NOT NULL,
    certificate_template_id INTEGER NOT NULL,
    template_variables JSONB,
    tenant_id INTEGER NOT NULL,
    created_by VARCHAR(255) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    -- Foreign key constraints
    CONSTRAINT fk_event_certificates_event_id 
        FOREIGN KEY (event_id) REFERENCES events(id) ON DELETE CASCADE,
    CONSTRAINT fk_event_certificates_certificate_template_id 
        FOREIGN KEY (certificate_template_id) REFERENCES certificate_templates(id) ON DELETE CASCADE,
    CONSTRAINT fk_event_certificates_tenant_id 
        FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE
);

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_event_certificates_event_id ON event_certificates(event_id);
CREATE INDEX IF NOT EXISTS idx_event_certificates_tenant_id ON event_certificates(tenant_id);
CREATE INDEX IF NOT EXISTS idx_event_certificates_template_id ON event_certificates(certificate_template_id);

-- Add updated_at trigger
CREATE OR REPLACE FUNCTION update_event_certificates_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_event_certificates_updated_at
    BEFORE UPDATE ON event_certificates
    FOR EACH ROW
    EXECUTE FUNCTION update_event_certificates_updated_at();