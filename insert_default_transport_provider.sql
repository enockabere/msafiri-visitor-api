-- Insert default transport provider for absolute_cabs
INSERT INTO transport_providers (
    tenant_id,
    provider_name,
    is_enabled,
    client_id,
    client_secret,
    hmac_secret,
    api_base_url,
    token_url,
    created_by,
    created_at
) VALUES (
    1,  -- tenant_id for msf-oca
    'absolute_cabs',
    false,  -- disabled by default
    '',
    '',
    '',
    '',
    '',
    'system',
    NOW()
) ON CONFLICT DO NOTHING;