# File: app/api/v1/endpoints/vetting_email_templates.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app.db.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.models.vetting_email_template import VettingEmailTemplate
from app.models.vetting_committee import VettingCommittee
from app.schemas.vetting_email_template import (
    VettingEmailTemplateCreate,
    VettingEmailTemplateUpdate,
    VettingEmailTemplateResponse
)

router = APIRouter()

@router.post("/committee/{committee_id}/templates", response_model=VettingEmailTemplateResponse)
def create_or_update_email_template(
    committee_id: int,
    template_data: VettingEmailTemplateCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create or update email template for vetting committee (Approver only)"""

    # Verify committee exists and user is approver
    committee = db.query(VettingCommittee).filter(VettingCommittee.id == committee_id).first()
    if not committee:
        raise HTTPException(status_code=404, detail="Committee not found")

    if committee.approver_id != current_user.id and current_user.email != committee.approver_email:
        raise HTTPException(status_code=403, detail="Only approver can manage templates")

    # Check if template exists
    existing = db.query(VettingEmailTemplate).filter(
        VettingEmailTemplate.committee_id == committee_id,
        VettingEmailTemplate.template_type == template_data.template_type
    ).first()

    if existing:
        # Update existing
        existing.subject = template_data.subject
        existing.content = template_data.content
        db.commit()
        db.refresh(existing)
        return existing
    else:
        # Create new
        template = VettingEmailTemplate(
            committee_id=committee_id,
            template_type=template_data.template_type,
            subject=template_data.subject,
            content=template_data.content,
            created_by=current_user.email
        )
        db.add(template)
        db.commit()
        db.refresh(template)
        return template

@router.get("/committee/{committee_id}/templates", response_model=List[VettingEmailTemplateResponse])
def get_email_templates(
    committee_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get all email templates for a committee"""

    committee = db.query(VettingCommittee).filter(VettingCommittee.id == committee_id).first()
    if not committee:
        raise HTTPException(status_code=404, detail="Committee not found")

    # Only approver can view templates
    if committee.approver_id != current_user.id and current_user.email != committee.approver_email:
        raise HTTPException(status_code=403, detail="Only approver can view templates")

    templates = db.query(VettingEmailTemplate).filter(
        VettingEmailTemplate.committee_id == committee_id
    ).all()

    return templates

@router.delete("/templates/{template_id}")
def delete_email_template(
    template_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete email template"""

    template = db.query(VettingEmailTemplate).filter(VettingEmailTemplate.id == template_id).first()
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")

    # Verify user is approver
    committee = db.query(VettingCommittee).filter(VettingCommittee.id == template.committee_id).first()
    if not committee or (committee.approver_id != current_user.id and current_user.email != committee.approver_email):
        raise HTTPException(status_code=403, detail="Only approver can delete templates")

    db.delete(template)
    db.commit()
    return {"message": "Template deleted successfully"}
