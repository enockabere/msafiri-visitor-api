# File: app/core/config.py (FIXED - Complete Settings)
from pydantic_settings import BaseSettings
from typing import Optional
import os

class Settings(BaseSettings):
    # Database - Updated for Render
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL", 
        "postgresql://postgres:admin@localhost:5432/msafiri_db"  # Local fallback
    )
    
    # Security
    SECRET_KEY: str = "jkslksnskswjdslksmslswkdjdndldndl"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # API
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "Msafiri Visitor System"
    
    # Environment
    ENVIRONMENT: str = "development"
    DEBUG: bool = False
    LOG_LEVEL: str = "INFO"
    
    # Microsoft SSO Configuration
    AZURE_TENANT_ID: Optional[str] = None
    AZURE_CLIENT_ID: Optional[str] = None
    AZURE_CLIENT_SECRET: Optional[str] = None
    
    # Email Configuration (ENHANCED)
    SMTP_SERVER: str = "smtp.gmail.com"  
    SMTP_PORT: int = 587
    SMTP_USERNAME: str = "maebaenock95@gmail.com"  # Updated
    SMTP_PASSWORD: str = "bkmqbwljghtimrws" 
    FROM_EMAIL: str = "maebaenock95@gmail.com"
    FROM_NAME: str = "Msafiri Team"  # New
    
    # Email Features
    SEND_EMAILS: bool = True  # Toggle to disable emails in development
    EMAIL_TIMEOUT: int = 10  # Timeout for SMTP connections
    
    # Push Notifications (NEW)
    FIREBASE_SERVICE_ACCOUNT_PATH: Optional[str] = None
    FIREBASE_PROJECT_ID: Optional[str] = None
    ONESIGNAL_APP_ID: Optional[str] = None
    ONESIGNAL_API_KEY: Optional[str] = None
    
    # Frontend URLs
    FRONTEND_URL: str = "http://localhost:3000"
    MOBILE_DEEP_LINK: str = "msafiri://auth"
    
    # Notification Settings (NEW)
    DEFAULT_NOTIFICATION_PRIORITY: str = "medium"
    AUTO_SEND_WELCOME_EMAILS: bool = True
    AUTO_SEND_STATUS_CHANGE_EMAILS: bool = True
    
    # WebSocket for real-time notifications (NEW)
    ENABLE_WEBSOCKET_NOTIFICATIONS: bool = True
    WEBSOCKET_HEARTBEAT_INTERVAL: int = 30
    
    class Config:
        env_file = ".env"
        # Allow extra fields from environment
        extra = "ignore"  # This will ignore extra fields instead of throwing errors

settings = Settings()