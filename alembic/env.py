from logging.config import fileConfig
from sqlalchemy import engine_from_config
from sqlalchemy import pool
from alembic import context
import os
import sys
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Add the project root to the path
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

# FIXED: Import database and Base first
from app.db.database import Base

# FIXED: Import ALL models explicitly to ensure they're registered
from app.models.base import BaseModel, TenantBaseModel
from app.models.tenant import Tenant
from app.models.user import User, UserRole, AuthProvider, UserStatus
from app.models.notification import Notification, NotificationType, NotificationPriority
from app.models.news_update import NewsUpdate
from app.models.chat import ChatRoom, ChatMessage, DirectMessage
from app.models.flight_itinerary import FlightItinerary
from app.models.transport_request import TransportRequest
from app.models.invitation import Invitation
from app.models.passport_record import PassportRecord
from app.models.app_feedback import AppFeedback
from app.models.travel_checklist_progress import TravelChecklistProgress
from app.models.participant_voucher_redemption import ParticipantVoucherRedemption
from app.models.pending_voucher_redemption import PendingVoucherRedemption
from app.models.travel_ticket import TravelTicket

# this is the Alembic Config object
config = context.config

# Interpret the config file for Python logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# FIXED: Set target metadata with explicit model registration
target_metadata = Base.metadata

def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    # Use DATABASE_URL from environment or fallback to config
    url = os.getenv("DATABASE_URL") or config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,  # Enable type comparison
        compare_server_default=True,  # Enable default comparison
    )

    with context.begin_transaction():
        context.run_migrations()

def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    # Override sqlalchemy.url with DATABASE_URL from environment if available
    configuration = config.get_section(config.config_ini_section, {})
    database_url = os.getenv("DATABASE_URL")
    if database_url:
        configuration["sqlalchemy.url"] = database_url
    
    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection, 
            target_metadata=target_metadata,
            compare_type=True,  # Enable type comparison
            compare_server_default=True,  # Enable default comparison
        )

        with context.begin_transaction():
            context.run_migrations()

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()