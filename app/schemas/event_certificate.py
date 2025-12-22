from pydantic import BaseModel
from typing import Optional, Dict, Any
from datetime import datetime

class EventCertificateBase(BaseModel):
    certificate_template_id: int
    template_variables: Dict[str, Any]

class EventCertificateCreate(EventCertificateBase):
    pass

class EventCertificateUpdate(BaseModel):
    certificate_template_id: Optional[int] = None
    template_variables: Optional[Dict[str, Any]] = None

class EventCertificateResponse(EventCertificateBase):
    id: int
    event_id: int
    tenant_id: int
    created_by: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class ParticipantCertificateResponse(BaseModel):
    id: int
    event_certificate_id: int
    participant_id: int
    certificate_url: Optional[str] = None
    certificate_public_id: Optional[str] = None
    issued_at: datetime

    class Config:
        from_attributes = True