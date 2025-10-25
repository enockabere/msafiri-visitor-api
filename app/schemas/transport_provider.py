from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class TransportProviderBase(BaseModel):
    provider_name: str
    is_enabled: bool = False
    client_id: Optional[str] = None
    api_base_url: Optional[str] = None
    token_url: Optional[str] = None

class TransportProviderCreate(TransportProviderBase):
    client_secret: Optional[str] = None
    hmac_secret: Optional[str] = None

class TransportProviderUpdate(BaseModel):
    is_enabled: Optional[bool] = None
    client_id: Optional[str] = None
    client_secret: Optional[str] = None
    hmac_secret: Optional[str] = None
    api_base_url: Optional[str] = None
    token_url: Optional[str] = None

class TransportProvider(TransportProviderBase):
    id: int
    tenant_id: int
    created_by: str
    updated_by: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True