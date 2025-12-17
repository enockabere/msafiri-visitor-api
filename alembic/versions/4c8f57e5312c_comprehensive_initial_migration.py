"""comprehensive_initial_migration

Revision ID: 4c8f57e5312c
Revises: 
Create Date: 2025-12-12 13:34:50.724523

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '4c8f57e5312c'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Import models to create all tables
    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
    
    # Import all models individually to avoid import * issue
    from app.db.database import Base
    import app.models.tenant
    import app.models.user
    import app.models.user_tenants
    import app.models.event
    import app.models.event_participant
    import app.models.event_allocation
    import app.models.accommodation
    import app.models.transport_request
    import app.models.flight_itinerary
    import app.models.news_update
    import app.models.notification
    import app.models.chat
    import app.models.participant_voucher_redemption
    import app.models.pending_voucher_redemption
    
    # Get the current connection
    connection = op.get_bind()
    
    # Create all tables
    Base.metadata.create_all(bind=connection)


def downgrade() -> None:
    # Import models
    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
    
    # Import all models individually
    from app.db.database import Base
    import app.models.tenant
    import app.models.user
    import app.models.user_tenants
    import app.models.event
    import app.models.event_participant
    import app.models.event_allocation
    import app.models.accommodation
    import app.models.transport_request
    import app.models.flight_itinerary
    import app.models.news_update
    import app.models.notification
    import app.models.chat
    import app.models.participant_voucher_redemption
    import app.models.pending_voucher_redemption
    
    # Get the current connection
    connection = op.get_bind()
    
    # Drop all tables
    Base.metadata.drop_all(bind=connection)