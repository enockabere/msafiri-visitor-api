from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
import qrcode
from io import BytesIO
import base64
import os
from datetime import datetime
import re

from app.db.database import get_db
from app.core.deps import get_current_active_user
from app.api.deps import get_tenant_context
from app.crud.poa_template import poa_template
from app.schemas.poa_template import POATemplateResponse, POATemplateCreate, POATemplateUpdate
from app.models.user import User
from app.models.tenant import Tenant
from app.models.guesthouse import VendorAccommodation
from app.models.event_participant import EventParticipant
from app.models.event import Event

router = APIRouter()

@router.get("/vendor/{vendor_id}", response_model=POATemplateResponse)
def get_poa_template_by_vendor(
    vendor_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    tenant_slug: str = Depends(get_tenant_context)
) -> POATemplateResponse:
    """Get POA template for a specific vendor hotel"""
    # Get tenant
    tenant = db.query(Tenant).filter(Tenant.slug == tenant_slug).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    template = poa_template.get_by_vendor(db, vendor_accommodation_id=vendor_id)
    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="POA template not found for this vendor"
        )

    return template

@router.get("/", response_model=List[POATemplateResponse])
def get_poa_templates(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    tenant_slug: str = Depends(get_tenant_context)
) -> List[POATemplateResponse]:
    """Get all POA templates for tenant"""
    # Get tenant
    tenant = db.query(Tenant).filter(Tenant.slug == tenant_slug).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    templates = poa_template.get_by_tenant(db, tenant_id=tenant.id)
    return templates

@router.post("/", response_model=POATemplateResponse)
def create_poa_template(
    *,
    db: Session = Depends(get_db),
    template_in: POATemplateCreate,
    current_user: User = Depends(get_current_active_user),
    tenant_slug: str = Depends(get_tenant_context)
) -> POATemplateResponse:
    """Create new POA template for a vendor hotel"""
    # Get tenant
    tenant = db.query(Tenant).filter(Tenant.slug == tenant_slug).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    # Check if vendor exists and belongs to tenant
    vendor = db.query(VendorAccommodation).filter(
        VendorAccommodation.id == template_in.vendor_accommodation_id,
        VendorAccommodation.tenant_id == tenant.id
    ).first()
    if not vendor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Vendor hotel not found"
        )

    # Check if template already exists for this vendor
    existing_template = poa_template.get_by_vendor(db, vendor_accommodation_id=template_in.vendor_accommodation_id)
    if existing_template:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="POA template already exists for this vendor hotel. Please update the existing template."
        )

    template = poa_template.create_with_tenant(
        db=db,
        obj_in=template_in,
        tenant_id=tenant.id,
        created_by=current_user.id
    )
    return template

@router.put("/{template_id}", response_model=POATemplateResponse)
def update_poa_template(
    *,
    db: Session = Depends(get_db),
    template_id: int,
    template_in: POATemplateUpdate,
    current_user: User = Depends(get_current_active_user),
    tenant_slug: str = Depends(get_tenant_context)
) -> POATemplateResponse:
    """Update POA template"""
    # Get tenant
    tenant = db.query(Tenant).filter(Tenant.slug == tenant_slug).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    template = poa_template.get(db=db, id=template_id)
    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Template not found"
        )

    # Verify tenant ownership
    if template.tenant_id != tenant.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to update this template"
        )

    template = poa_template.update(db=db, db_obj=template, obj_in=template_in)
    return template

@router.delete("/{template_id}")
def delete_poa_template(
    *,
    db: Session = Depends(get_db),
    template_id: int,
    current_user: User = Depends(get_current_active_user),
    tenant_slug: str = Depends(get_tenant_context)
) -> dict:
    """Delete POA template"""
    # Get tenant
    tenant = db.query(Tenant).filter(Tenant.slug == tenant_slug).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    template = poa_template.get(db=db, id=template_id)
    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Template not found"
        )

    # Verify tenant ownership
    if template.tenant_id != tenant.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to delete this template"
        )

    poa_template.remove(db=db, id=template_id)
    return {"message": "Template deleted successfully"}

@router.get("/vendor/{vendor_id}/generate/{participant_id}")
async def generate_poa_from_template(
    vendor_id: int,
    participant_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    tenant_slug: str = Depends(get_tenant_context)
):
    """Generate POA HTML document for a participant at a vendor hotel"""
    # Get tenant
    tenant = db.query(Tenant).filter(Tenant.slug == tenant_slug).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    # Get POA template
    template = poa_template.get_by_vendor(db, vendor_accommodation_id=vendor_id)
    if not template:
        raise HTTPException(status_code=404, detail="POA template not found for this vendor")

    # Get vendor
    vendor = db.query(VendorAccommodation).filter(VendorAccommodation.id == vendor_id).first()
    if not vendor:
        raise HTTPException(status_code=404, detail="Vendor not found")

    # Get participant
    participant = db.query(EventParticipant).filter(EventParticipant.id == participant_id).first()
    if not participant:
        raise HTTPException(status_code=404, detail="Participant not found")

    # Get event
    event = None
    if participant.event_id:
        event = db.query(Event).filter(Event.id == participant.event_id).first()

    # Start with template content
    html_content = template.template_content

    # Replace logo placeholder
    if template.logo_url and '{{logo}}' in html_content:
        logo_html = f'<img src="{template.logo_url}" alt="Organization Logo" style="max-height: 100px; max-width: 300px; display: block; margin: 0 auto;" />'
        html_content = html_content.replace('{{logo}}', logo_html)

    # Replace signature placeholder
    if template.signature_url and '{{signature}}' in html_content:
        signature_html = f'<img src="{template.signature_url}" alt="Signature" style="max-height: 60px; max-width: 200px;" />'
        html_content = html_content.replace('{{signature}}', signature_html)

    # Generate QR code if enabled
    if template.enable_qr_code and '{{qrCode}}' in html_content:
        api_url = os.getenv('NEXT_PUBLIC_API_URL', 'http://localhost:8000')
        poa_url = f"{api_url}/api/v1/poa-templates/vendor/{vendor_id}/generate/{participant_id}"

        qr = qrcode.QRCode(version=1, box_size=10, border=2)
        qr.add_data(poa_url)
        qr.make(fit=True)
        qr_img = qr.make_image(fill_color="black", back_color="white")

        buffer = BytesIO()
        qr_img.save(buffer, format='PNG')
        qr_base64 = base64.b64encode(buffer.getvalue()).decode()
        qr_img_tag = f'<img src="data:image/png;base64,{qr_base64}" alt="QR Code" style="width: 100px; height: 100px;" />'

        html_content = html_content.replace('{{qrCode}}', qr_img_tag)

    # Replace participant variables
    variables = {
        'participantName': participant.full_name or '',
        'participantEmail': participant.email or '',
        'participantPhone': participant.phone or participant.phone_number or '',
        'participantNationality': participant.nationality or '',
        'participantPassport': participant.passport_number or '',
        'participantGender': participant.gender or '',

        # Vendor/Hotel details
        'hotelName': vendor.vendor_name,
        'hotelLocation': vendor.location or '',
        'hotelPhone': vendor.contact_phone or '',
        'hotelEmail': vendor.contact_email or '',
        'hotelContactPerson': vendor.contact_person or '',

        # Event details
        'eventTitle': event.title if event else '',
        'eventStartDate': event.start_date.strftime('%B %d, %Y') if event and event.start_date else '',
        'eventEndDate': event.end_date.strftime('%B %d, %Y') if event and event.end_date else '',
        'eventLocation': event.location if event else '',

        # Document info
        'documentDate': datetime.now().strftime('%B %d, %Y'),
        'tenantName': tenant.name or '',
    }

    # Replace all placeholders
    for key, value in variables.items():
        html_content = html_content.replace(f'{{{{{key}}}}}', str(value))

    return HTMLResponse(content=html_content)
