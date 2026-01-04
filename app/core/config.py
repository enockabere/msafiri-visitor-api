from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional
import os


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",  
    )

    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "postgresql://postgres:admin@localhost:5432/msafiri_db",
    )

    SECRET_KEY: str = os.getenv("SECRET_KEY", "jkslksnskswjdslksmslswkdjdndldndl")
    ALGORITHM: str = os.getenv("ALGORITHM", "HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "1440"))  # 24 hours instead of 30 minutes


    API_V1_STR: str = os.getenv("API_V1_STR", "/api/v1")
    PROJECT_NAME: str = os.getenv("PROJECT_NAME", "Msafiri Visitor System")


    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development") 
    DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")


    AZURE_TENANT_ID: Optional[str] = os.getenv("AZURE_TENANT_ID")
    AZURE_CLIENT_ID: Optional[str] = os.getenv("AZURE_CLIENT_ID")
    AZURE_CLIENT_SECRET: Optional[str] = os.getenv("AZURE_CLIENT_SECRET")


    SMTP_SERVER: str = os.getenv("SMTP_SERVER", "smtp.gmail.com")
    SMTP_PORT: int = int(os.getenv("SMTP_PORT", "587"))
    SMTP_USERNAME: str = os.getenv("SMTP_USERNAME", "maebaenock95@gmail.com")
    SMTP_PASSWORD: str = os.getenv("SMTP_PASSWORD", "bkmqbwljghtimrws")
    FROM_EMAIL: str = os.getenv("FROM_EMAIL", "maebaenock95@gmail.com")
    FROM_NAME: str = os.getenv("FROM_NAME", "Msafiri Team")
    SEND_EMAILS: bool = os.getenv("SEND_EMAILS", "true").lower() == "true"
    EMAIL_TIMEOUT: int = int(os.getenv("EMAIL_TIMEOUT", "10"))

    FIREBASE_SERVICE_ACCOUNT_PATH: Optional[str] = os.getenv("FIREBASE_SERVICE_ACCOUNT_PATH")
    FIREBASE_PROJECT_ID: Optional[str] = os.getenv("FIREBASE_PROJECT_ID")
    ONESIGNAL_APP_ID: Optional[str] = os.getenv("ONESIGNAL_APP_ID")
    ONESIGNAL_API_KEY: Optional[str] = os.getenv("ONESIGNAL_API_KEY")


    FRONTEND_URL: str = os.getenv("FRONTEND_URL", "http://199.160.120.48:3000")
    MOBILE_DEEP_LINK: str = os.getenv("MOBILE_DEEP_LINK", "msafiri://auth")


    DEFAULT_NOTIFICATION_PRIORITY: str = os.getenv("DEFAULT_NOTIFICATION_PRIORITY", "medium")
    AUTO_SEND_WELCOME_EMAILS: bool = os.getenv("AUTO_SEND_WELCOME_EMAILS", "true").lower() == "true"
    AUTO_SEND_STATUS_CHANGE_EMAILS: bool = os.getenv("AUTO_SEND_STATUS_CHANGE_EMAILS", "true").lower() == "true"

    ENABLE_WEBSOCKET_NOTIFICATIONS: bool = (
        os.getenv("ENABLE_WEBSOCKET_NOTIFICATIONS", "true").lower() == "true"
    )
    WEBSOCKET_HEARTBEAT_INTERVAL: int = int(os.getenv("WEBSOCKET_HEARTBEAT_INTERVAL", "30"))

    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT.lower() == "production"

    @property
    def is_development(self) -> bool:
        return self.ENVIRONMENT.lower() == "development"

    @property
    def frontend_url(self) -> str:
        # Always use FRONTEND_URL from environment if set
        return self.FRONTEND_URL


settings = Settings()
