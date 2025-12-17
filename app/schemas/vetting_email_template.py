# File: app/schemas/vetting_email_template.py
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class VettingEmailTemplateCreate(BaseModel):
    template_type: str  # "selected" or "not_selected"
    subject: str
    content: str

class VettingEmailTemplateUpdate(BaseModel):
    subject: Optional[str] = None
    content: Optional[str] = None

class VettingEmailTemplateResponse(BaseModel):
    id: int
    committee_id: int
    template_type: str
    subject: str
    content: str
    created_by: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
