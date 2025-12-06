-- Create event_voucher_scanners table for event-specific scanner tracking

CREATE TABLE IF NOT EXISTS event_voucher_scanners (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL,
    event_id INTEGER NOT NULL,
    tenant_id INTEGER NOT NULL,
    created_by VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE,
    CONSTRAINT fk_event_voucher_scanners_event FOREIGN KEY (event_id) REFERENCES events(id) ON DELETE CASCADE,
    CONSTRAINT fk_event_voucher_scanners_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    CONSTRAINT uq_user_event_scanner UNIQUE (user_id, event_id)
);

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_event_voucher_scanners_event_id ON event_voucher_scanners(event_id);
CREATE INDEX IF NOT EXISTS idx_event_voucher_scanners_user_id ON event_voucher_scanners(user_id);
CREATE INDEX IF NOT EXISTS idx_event_voucher_scanners_tenant_id ON event_voucher_scanners(tenant_id);
CREATE INDEX IF NOT EXISTS idx_event_voucher_scanners_active ON event_voucher_scanners(is_active);
