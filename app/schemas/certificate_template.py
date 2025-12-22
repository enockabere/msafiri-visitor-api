from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

class CertificateTemplateBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255, description="Template name")
    description: Optional[str] = Field(None, description="Template description")
    template_content: str = Field(..., min_length=1, description="HTML template content")
    logo_url: Optional[str] = Field(None, description="Logo image URL")
    logo_public_id: Optional[str] = Field(None, description="Logo Cloudinary public ID")

class CertificateTemplateCreate(CertificateTemplateBase):
    pass

class CertificateTemplateUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255, description="Template name")
    description: Optional[str] = Field(None, description="Template description")
    template_content: Optional[str] = Field(None, min_length=1, description="HTML template content")
    logo_url: Optional[str] = Field(None, description="Logo image URL")
    logo_public_id: Optional[str] = Field(None, description="Logo Cloudinary public ID")

class CertificateTemplateResponse(CertificateTemplateBase):
    id: int
    tenant_id: int
    created_by: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True