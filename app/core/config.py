from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    # Database
    
    DATABASE_URL: str = "postgresql://postgres:admin@localhost:5432/msafiri_db"
    
    # Security
    SECRET_KEY: str = "jkdfjwdkwdlkjwdfnwodwinwkndqwokwqbnwjdqiowodikwjb"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # API
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "Msafiri Visitor System"
    
    class Config:
        env_file = ".env"
        
settings = Settings()