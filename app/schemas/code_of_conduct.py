# File: app/schemas/code_of_conduct.py
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class CodeOfConductCreate(BaseModel):
    title: str
    content: Optional[str] = None  # Rich text HTML
    url: Optional[str] = None  # URL to external code of conduct
    version: Optional[str] = None
    effective_date: Optional[datetime] = None

class CodeOfConductUpdate(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None
    url: Optional[str] = None
    version: Optional[str] = None
    effective_date: Optional[datetime] = None
    is_active: Optional[bool] = None

class CodeOfConductResponse(BaseModel):
    id: int
    title: str
    content: Optional[str]
    url: Optional[str]
    tenant_id: str
    is_active: bool
    version: Optional[str]
    effective_date: Optional[datetime]
    created_by: str
    updated_by: Optional[str]
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True