from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
import os

from app.db.database import get_db
from app.core.deps import get_current_active_user
from app.api.deps import get_tenant_context
from app.crud.invitation_template import invitation_template
from app.schemas.invitation_template import InvitationTemplate, InvitationTemplateCreate, InvitationTemplateUpdate
from app.models.user import User
from app.models.tenant import Tenant
from app.models.event_participant import EventParticipant
from app.services.loi_generation import generate_loi_document

router = APIRouter()

@router.get("/", response_model=dict)
def get_invitation_templates(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    tenant_slug: str = Depends(get_tenant_context),
    skip: int = 0,
    limit: int = 100,
) -> dict:
    """
    Retrieve invitation templates for the current tenant.
    """
    try:
        # Get tenant ID from slug
        tenant = db.query(Tenant).filter(Tenant.slug == tenant_slug).first()
        if not tenant:
            raise HTTPException(status_code=404, detail="Tenant not found")
        
        templates = invitation_template.get_by_tenant(db, tenant_id=tenant.id, skip=skip, limit=limit)
        # Convert to dict to ensure proper serialization
        template_list = []
        for template in templates:
            # Log LOI template name and status
            print(f"[LOI] Template: '{template.name}' - Status: {'ACTIVE' if template.is_active else 'INACTIVE'} - Tenant: {tenant.slug}")
            
            template_dict = {
                "id": template.id,
                "name": template.name,
                "description": template.description,
                "template_content": template.template_content,
                "logo_url": template.logo_url,
                "logo_public_id": template.logo_public_id,
                "watermark_url": template.watermark_url,
                "watermark_public_id": template.watermark_public_id,
                "signature_url": template.signature_url,
                "signature_public_id": template.signature_public_id,
                "enable_qr_code": template.enable_qr_code,
                "is_active": template.is_active,
                "address_fields": template.address_fields or [],
                "signature_footer_fields": template.signature_footer_fields or [],
                "created_at": template.created_at.isoformat() if template.created_at else None,
                "updated_at": template.updated_at.isoformat() if template.updated_at else None
            }
            template_list.append(template_dict)
        
        print(f"[LOI] Total templates found for tenant {tenant.slug}: {len(template_list)}")
        return {"templates": template_list}
    except Exception as e:
        print(f"Error loading templates: {e}")
        return {"templates": []}

@router.post("/", response_model=InvitationTemplate)
def create_invitation_template(
    *,
    db: Session = Depends(get_db),
    template_in: InvitationTemplateCreate,
    current_user: User = Depends(get_current_active_user),
    tenant_slug: str = Depends(get_tenant_context),
) -> InvitationTemplate:
    """
    Create new invitation template.
    """
    # Get tenant ID from slug
    tenant = db.query(Tenant).filter(Tenant.slug == tenant_slug).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    
    # Check if template with same name exists for this tenant
    existing_template = invitation_template.get_by_name(db, name=template_in.name, tenant_id=tenant.id)
    if existing_template:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Template with this name already exists"
        )
    
    # Add tenant_id to the template data
    template_data = template_in.dict()
    template_data['tenant_id'] = tenant.id
    
    template = invitation_template.create(db=db, obj_in=template_data)
    return template

@router.get("/{template_id}", response_model=InvitationTemplate)
def get_invitation_template(
    *,
    db: Session = Depends(get_db),
    template_id: int,
    current_user: User = Depends(get_current_active_user),
) -> InvitationTemplate:
    """
    Get invitation template by ID.
    """
    template = invitation_template.get(db=db, id=template_id)
    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Template not found"
        )
    return template

@router.put("/{template_id}", response_model=InvitationTemplate)
def update_invitation_template(
    *,
    db: Session = Depends(get_db),
    template_id: int,
    template_in: InvitationTemplateUpdate,
    current_user: User = Depends(get_current_active_user),
) -> InvitationTemplate:
    """
    Update invitation template.
    """
    template = invitation_template.get(db=db, id=template_id)
    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Template not found"
        )
    
    template = invitation_template.update(db=db, db_obj=template, obj_in=template_in)
    return template

@router.delete("/{template_id}")
def delete_invitation_template(
    *,
    db: Session = Depends(get_db),
    template_id: int,
    current_user: User = Depends(get_current_active_user),
) -> dict:
    """
    Delete invitation template.
    """
    template = invitation_template.get(db=db, id=template_id)
    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Template not found"
        )
    
    invitation_template.remove(db=db, id=template_id)
    return {"message": "Template deleted successfully"}

@router.get("/{template_id}/generate/{participant_id}")
async def generate_loi_from_template(
    template_id: int,
    participant_id: int,
    db: Session = Depends(get_db),
):
    """Generate LOI HTML from template for a participant"""
    from fastapi.responses import HTMLResponse
    import re
    from datetime import datetime
    
    print(f"\n[LOI] Generating LOI for template {template_id}, participant {participant_id}")
    
    # Get the invitation template
    template = invitation_template.get(db=db, id=template_id)
    if not template or not template.is_active:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Active invitation template not found"
        )
    
    print(f"[LOI] Template found: {template.name}")
    print(f"[LOI] Template content length: {len(template.template_content) if template.template_content else 0}")
    print(f"[LOI] Logo URL: {template.logo_url}")
    print(f"[LOI] Signature URL: {template.signature_url}")
    print(f"[LOI] Address fields: {template.address_fields}")
    print(f"[LOI] Signature footer: {template.signature_footer_fields}")
    
    # Get the participant
    participant = db.query(EventParticipant).filter(
        EventParticipant.id == participant_id
    ).first()
    
    if not participant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Participant not found"
        )
    
    print(f"[LOI] Participant: {participant.full_name}")
    
    # Get event details
    from app.models.event import Event
    event = db.query(Event).filter(Event.id == participant.event_id).first()
    
    print(f"[LOI] Event: {event.title if event else 'Not found'}")
    
    try:
        # Start with template HTML - this should be the saved template content
        html_content = template.template_content or ''
        
        print(f"[LOI] Template content preview (first 500 chars):")
        print(f"     {html_content[:500]}")
        
        # Ensure proper HTML structure
        if not html_content.strip().startswith('<!DOCTYPE html>') and not html_content.strip().startswith('<html'):
            frontend_url = os.getenv('FRONTEND_URL', 'http://localhost:3000/portal')
            html_content = f'''<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8">
  <title>Letter of Invitation</title>
  <link rel="icon" type="image/x-icon" href="{frontend_url}/favicon.ico">
</head>
<body>
{html_content}
</body>
</html>'''
        
        # Prepare template variables with actual participant data
        event_name = event.title if event else f"Event {participant.event_id}"
        event_dates = f"{event.start_date.strftime('%B %d')} - {event.end_date.strftime('%B %d, %Y')}" if event and event.start_date and event.end_date else "TBD"
        event_location = event.location if event else "TBD"
        
        # Get participant passport data if available
        passport_number = getattr(participant, 'passport_number', None) or 'N/A'
        nationality = getattr(participant, 'nationality', None) or 'N/A'
        date_of_birth = getattr(participant, 'date_of_birth', None)
        if date_of_birth and hasattr(date_of_birth, 'strftime'):
            date_of_birth = date_of_birth.strftime('%Y-%m-%d')
        else:
            date_of_birth = str(date_of_birth) if date_of_birth else 'N/A'
        
        passport_issue_date = getattr(participant, 'passport_issue_date', None)
        if passport_issue_date and hasattr(passport_issue_date, 'strftime'):
            passport_issue_date = passport_issue_date.strftime('%Y-%m-%d')
        else:
            passport_issue_date = str(passport_issue_date) if passport_issue_date else 'N/A'
            
        passport_expiry_date = getattr(participant, 'passport_expiry_date', None)
        if passport_expiry_date and hasattr(passport_expiry_date, 'strftime'):
            passport_expiry_date = passport_expiry_date.strftime('%Y-%m-%d')
        else:
            passport_expiry_date = str(passport_expiry_date) if passport_expiry_date else 'N/A'
        
        print(f"[LOI] Participant data:")
        print(f"     Name: {participant.full_name}")
        print(f"     Passport: {passport_number}")
        print(f"     Nationality: {nationality}")
        print(f"     DOB: {date_of_birth}")
        
        variables = {
            'participantName': participant.full_name,
            'participant_name': participant.full_name,
            'eventName': event_name,
            'event_name': event_name,
            'eventDates': event_dates,
            'event_dates': event_dates,
            'eventLocation': event_location,
            'event_location': event_location,
            'organizationName': 'MSF',
            'organization_name': 'MSF',
            'currentDate': datetime.now().strftime('%B %d, %Y'),
            'passportNumber': passport_number,
            'passport_number': passport_number,
            'nationality': nationality,
            'dateOfBirth': date_of_birth,
            'date_of_birth': date_of_birth,
            'passport_issue_date': passport_issue_date,
            'passport_expiry_date': passport_expiry_date,
            'event_start_date': event.start_date.strftime('%Y-%m-%d') if event and event.start_date else 'TBD',
            'event_end_date': event.end_date.strftime('%Y-%m-%d') if event and event.end_date else 'TBD',
            'accommodation_details': event_location if event_location != 'TBD' else 'Hotel accommodation will be provided',
        }
        
        print(f"[LOI] Variables prepared: {len(variables)} items")
        
        # Replace template variables
        for key, value in variables.items():
            pattern = f'{{{{\\s*{key}\\s*}}}}'
            if re.search(pattern, html_content, flags=re.IGNORECASE):
                html_content = re.sub(pattern, str(value), html_content, flags=re.IGNORECASE)
                print(f"[LOI] Replaced {key} with {str(value)[:50]}...")
        
        # Add logo if available
        if template.logo_url:
            logo_html = f'<img src="{template.logo_url}" alt="Logo" style="max-width: 200px; height: auto;" />'
            html_content = html_content.replace('{{logo}}', logo_html)
            print(f"[LOI] Logo replaced with: {template.logo_url}")
        else:
            html_content = html_content.replace('{{logo}}', '')
            print(f"[LOI] No logo URL found")
        
        # Add signature if available
        if template.signature_url:
            signature_html = f'<img src="{template.signature_url}" alt="Signature" style="max-width: 120px; max-height: 60px; height: auto; display: block; margin-bottom: 10px;" />'
            html_content = html_content.replace('{{signature}}', signature_html)
            print(f"[LOI] Signature replaced with: {template.signature_url}")
        else:
            html_content = html_content.replace('{{signature}}', '')
            print(f"[LOI] No signature URL found")
        
        # Add address fields from template
        if template.address_fields:
            if isinstance(template.address_fields, list):
                address_text = '<br>'.join(template.address_fields)
            else:
                address_text = str(template.address_fields).replace('\n', '<br>')
            html_content = html_content.replace('{{organization_address}}', address_text)
            print(f"[LOI] Address replaced with: {address_text[:100]}...")
        else:
            html_content = html_content.replace('{{organization_address}}', 'MSF Kenya, Nairobi')
            print(f"[LOI] No address fields found, using default")
        
        # Add signature footer from template
        if template.signature_footer_fields:
            if isinstance(template.signature_footer_fields, list):
                footer_text = '<br>'.join(template.signature_footer_fields)
            else:
                footer_text = str(template.signature_footer_fields).replace('\n', '<br>')
            html_content = html_content.replace('{{signature_footer}}', footer_text)
            print(f"[LOI] Signature footer replaced with: {footer_text[:100]}...")
        else:
            html_content = html_content.replace('{{signature_footer}}', '')
            print(f"[LOI] No signature footer found")
        
        # Add watermark if available
        if template.watermark_url:
            # Add watermark using pseudo-element that works on all pages
            watermark_css = f'''
            <style>
                body {{
                    position: relative;
                }}
                body::before {{
                    content: "";
                    position: fixed;
                    top: 0;
                    left: 0;
                    width: 100%;
                    height: 100%;
                    background-image: url('{template.watermark_url}');
                    background-repeat: no-repeat;
                    background-position: center;
                    background-size: 400px auto;
                    opacity: 0.1;
                    z-index: -1;
                    pointer-events: none;
                }}
            </style>
            '''
            # Insert watermark CSS in head
            if '</head>' in html_content:
                html_content = html_content.replace('</head>', f'{watermark_css}</head>')
            print(f"[LOI] Watermark CSS added: {template.watermark_url}")
        
        # Generate QR code if enabled
        if template.enable_qr_code:
            # Use FRONTEND_URL from environment (already includes /portal)
            frontend_url = os.getenv('FRONTEND_URL', 'http://localhost:3000/portal')
            public_url = f"{frontend_url}/public/loi/{participant_id}-{event.id if event else 0}"
            # Generate actual QR code using Google Charts API (no dependencies needed)
            qr_code_url = f"https://api.qrserver.com/v1/create-qr-code/?size=150x150&data={public_url}"
            qr_code_html = f'''
            <div style="text-align: center; margin: 10px 0;">
                <img src="{qr_code_url}" alt="QR Code" style="width: 100px; height: 100px; border: 1px solid #ccc; padding: 5px;" />
                <div style="font-size: 10px; margin-top: 5px; color: #666;">Scan to verify document</div>
            </div>
            '''
            html_content = html_content.replace('{{qr_code}}', qr_code_html)
            print(f"[LOI] QR code generated for: {public_url}")
        else:
            html_content = html_content.replace('{{qr_code}}', '')
        
        # Add print styles and auto-print script
        html_content = html_content.replace('</head>', '''
            <style>
                @media print {
                    body { margin: 0; }
                    @page { margin: 0.5in; }
                }
            </style>
            <script>
                window.onload = function() {
                    setTimeout(function() {
                        window.print();
                    }, 500);
                };
            </script>
        </head>''')
        
        print(f"[LOI] Final HTML length: {len(html_content)}")
        print(f"[LOI] Generation complete")
        
        return HTMLResponse(content=html_content)
        
    except Exception as e:
        print(f"[LOI] Error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate LOI: {str(e)}"
        )

@router.get("/active/list", response_model=List[InvitationTemplate])
def get_active_invitation_templates(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    tenant_slug: str = Depends(get_tenant_context),
) -> List[InvitationTemplate]:
    """
    Get all active invitation templates for the current tenant.
    """
    # Get tenant ID from slug
    tenant = db.query(Tenant).filter(Tenant.slug == tenant_slug).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    
    return invitation_template.get_active_templates(db, tenant_id=tenant.id)
