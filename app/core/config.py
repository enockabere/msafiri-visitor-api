from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    # Database
    DATABASE_URL: str = "postgresql://postgres:admin@localhost:5432/msafiri_db"
    
    # Security
    SECRET_KEY: str = "jkslksnskswjdslksmslswkdjdndldndl"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # API
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "Msafiri Visitor System"
    
    # Microsoft SSO Configuration
    AZURE_TENANT_ID: Optional[str] = None
    AZURE_CLIENT_ID: Optional[str] = None
    AZURE_CLIENT_SECRET: Optional[str] = None
    
    # Email Configuration
    SMTP_SERVER: str = "smtp.gmail.com"  
    SMTP_PORT: int = 587
    SMTP_USERNAME: Optional[str] = "Enock Maeba"
    SMTP_PASSWORD: Optional[str] = "bkmqbwljghtimrws" 
    FROM_EMAIL: str = "maebaenock95@gmail.com"
    
    # Frontend URLs
    FRONTEND_URL: str = "http://localhost:3000"
    MOBILE_DEEP_LINK: str = "msafiri://auth"
    
    class Config:
        env_file = ".env"

settings = Settings()