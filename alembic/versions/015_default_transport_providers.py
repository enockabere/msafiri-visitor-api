"""insert_default_transport_providers

Revision ID: 015_default_transport_providers
Revises: 014_transport_providers
Create Date: 2024-12-19 10:30:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql import text


# revision identifiers, used by Alembic.
revision = '015_default_transport_providers'
down_revision = '014_transport_providers'
branch_labels = None
depends_on = None


def upgrade():
    # Insert default transport provider for absolute_cabs
    op.execute(text("""
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
            1,
            'absolute_cabs',
            false,
            '',
            '',
            '',
            '',
            '',
            'system',
            NOW()
        ) ON CONFLICT DO NOTHING;
    """))


def downgrade():
    # Remove the default transport provider
    op.execute(text("""
        DELETE FROM transport_providers 
        WHERE tenant_id = 1 AND provider_name = 'absolute_cabs' AND created_by = 'system';
    """))