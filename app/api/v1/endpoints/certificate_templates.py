from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app.db.database import get_db
from app.api.deps import get_current_user, get_tenant_context
from app.models.user import User
from app.models.tenant import Tenant
from app.models.certificate_template import CertificateTemplate
from app.schemas.certificate_template import CertificateTemplateCreate, CertificateTemplateUpdate, CertificateTemplateResponse

router = APIRouter()

@router.get("/", response_model=List[CertificateTemplateResponse])
def get_certificate_templates(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_slug: str = Depends(get_tenant_context)
):
    """Get all certificate templates for the current tenant"""
    # Get tenant ID from slug
    tenant = db.query(Tenant).filter(Tenant.slug == tenant_slug).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    
    templates = db.query(CertificateTemplate).filter(
        CertificateTemplate.tenant_id == tenant.id
    ).order_by(CertificateTemplate.created_at.desc()).all()
    
    return templates

@router.post("/", response_model=CertificateTemplateResponse)
def create_certificate_template(
    template_data: CertificateTemplateCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_slug: str = Depends(get_tenant_context)
):
    """Create a new certificate template"""
    # Check if user has permission to create templates
    # if current_user.role not in ["super_admin", "mt_admin", "hr_admin"]:
    #     raise HTTPException(status_code=403, detail="Insufficient permissions")
    
    # Get tenant ID from slug
    tenant = db.query(Tenant).filter(Tenant.slug == tenant_slug).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    
    # Check if template name already exists for this tenant
    existing_template = db.query(CertificateTemplate).filter(
        CertificateTemplate.tenant_id == tenant.id,
        CertificateTemplate.name == template_data.name
    ).first()
    
    if existing_template:
        raise HTTPException(status_code=400, detail="Template name already exists")
    
    template = CertificateTemplate(
        **template_data.dict(),
        tenant_id=tenant.id,
        created_by=current_user.id
    )
    
    db.add(template)
    db.commit()
    db.refresh(template)
    
    return template

@router.get("/{template_id}", response_model=CertificateTemplateResponse)
def get_certificate_template(
    template_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_slug: str = Depends(get_tenant_context)
):
    """Get a specific certificate template"""
    # Get tenant ID from slug
    tenant = db.query(Tenant).filter(Tenant.slug == tenant_slug).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    
    template = db.query(CertificateTemplate).filter(
        CertificateTemplate.id == template_id,
        CertificateTemplate.tenant_id == tenant.id
    ).first()
    
    if not template:
        raise HTTPException(status_code=404, detail="Certificate template not found")
    
    return template

@router.put("/{template_id}", response_model=CertificateTemplateResponse)
def update_certificate_template(
    template_id: int,
    template_data: CertificateTemplateUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_slug: str = Depends(get_tenant_context)
):
    """Update a certificate template"""
    # Check if user has permission to update templates
    # if current_user.role not in ["super_admin", "mt_admin", "hr_admin"]:
    #     raise HTTPException(status_code=403, detail="Insufficient permissions")
    
    # Get tenant ID from slug
    tenant = db.query(Tenant).filter(Tenant.slug == tenant_slug).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    
    template = db.query(CertificateTemplate).filter(
        CertificateTemplate.id == template_id,
        CertificateTemplate.tenant_id == tenant.id
    ).first()
    
    if not template:
        raise HTTPException(status_code=404, detail="Certificate template not found")
    
    # Check if new name conflicts with existing templates (if name is being changed)
    if template_data.name and template_data.name != template.name:
        existing_template = db.query(CertificateTemplate).filter(
            CertificateTemplate.tenant_id == tenant.id,
            CertificateTemplate.name == template_data.name,
            CertificateTemplate.id != template_id
        ).first()
        
        if existing_template:
            raise HTTPException(status_code=400, detail="Template name already exists")
    
    # Update template fields
    update_data = template_data.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(template, field, value)
    
    db.commit()
    db.refresh(template)
    
    return template

@router.delete("/{template_id}")
def delete_certificate_template(
    template_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_slug: str = Depends(get_tenant_context)
):
    """Delete a certificate template"""
    from app.models.event_certificate import EventCertificate

    # Check if user has permission to delete templates
    # if current_user.role not in ["super_admin", "mt_admin", "hr_admin"]:
    #     raise HTTPException(status_code=403, detail="Insufficient permissions")

    # Get tenant ID from slug
    tenant = db.query(Tenant).filter(Tenant.slug == tenant_slug).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    template = db.query(CertificateTemplate).filter(
        CertificateTemplate.id == template_id,
        CertificateTemplate.tenant_id == tenant.id
    ).first()

    if not template:
        raise HTTPException(status_code=404, detail="Certificate template not found")

    # Check if template is being used by any events
    events_using_template = db.query(EventCertificate).filter(
        EventCertificate.certificate_template_id == template_id
    ).count()

    if events_using_template > 0:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot delete template. It is currently being used by {events_using_template} event certificate(s). Please remove the template from all events first."
        )

    db.delete(template)
    db.commit()

    return {"message": "Certificate template deleted successfully"}