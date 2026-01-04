-- Create invitation_templates table
CREATE TABLE IF NOT EXISTS invitation_templates (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    template_content TEXT NOT NULL,
    logo_url VARCHAR(500),
    logo_public_id VARCHAR(255),
    watermark_url VARCHAR(500),
    watermark_public_id VARCHAR(255),
    signature_url VARCHAR(500),
    signature_public_id VARCHAR(255),
    enable_qr_code BOOLEAN DEFAULT true,
    is_active BOOLEAN DEFAULT true,
    address_fields JSON,
    signature_footer_fields JSON,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE
);

-- Create index
CREATE INDEX IF NOT EXISTS ix_invitation_templates_id ON invitation_templates (id);