from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.db.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.models.tenant import Tenant

router = APIRouter()

class EmailTemplateRequest(BaseModel):
    subject: str
    body: str

class EmailTemplateResponse(BaseModel):
    subject: str
    body: str
    tenant_slug: str

# Simple in-memory storage for now (replace with database later)
email_templates = {}

@router.get("/tenant/{tenant_slug}/vetting-notification", response_model=EmailTemplateResponse)
def get_email_template(
    tenant_slug: str,
    current_user: User = Depends(get_current_user)
):
    """Get email template for tenant"""
    template_key = f"{tenant_slug}_vetting_notification"
    template = email_templates.get(template_key)
    
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    
    return EmailTemplateResponse(
        subject=template["subject"],
        body=template["body"],
        tenant_slug=tenant_slug
    )

@router.put("/tenant/{tenant_slug}/vetting-notification", response_model=EmailTemplateResponse)
def save_email_template(
    tenant_slug: str,
    template_data: EmailTemplateRequest,
    current_user: User = Depends(get_current_user)
):
    """Save email template for tenant"""
    template_key = f"{tenant_slug}_vetting_notification"
    email_templates[template_key] = {
        "subject": template_data.subject,
        "body": template_data.body,
        "tenant_slug": tenant_slug
    }
    
    return EmailTemplateResponse(
        subject=template_data.subject,
        body=template_data.body,
        tenant_slug=tenant_slug
    )
