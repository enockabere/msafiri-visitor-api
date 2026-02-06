from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
import os

from app.db.database import get_db
from app.core.deps import get_current_active_user
from app.api.deps import get_tenant_context
from app.crud.badge_template import badge_template
from app.schemas.badge_template import BadgeTemplate, BadgeTemplateCreate, BadgeTemplateUpdate
from app.models.user import User
from app.models.tenant import Tenant
from app.models.event_participant import EventParticipant

router = APIRouter()

@router.get("/", response_model=dict)
def get_badge_templates(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    tenant_slug: str = Depends(get_tenant_context),
    skip: int = 0,
    limit: int = 100,
) -> dict:
    """
    Retrieve badge templates for the current tenant.
    """
    try:
        # Get tenant ID from slug
        tenant = db.query(Tenant).filter(Tenant.slug == tenant_slug).first()
        if not tenant:
            raise HTTPException(status_code=404, detail="Tenant not found")
        
        templates = badge_template.get_by_tenant(db, tenant_id=tenant.id, skip=skip, limit=limit)
        template_list = []
        for template in templates:
            print(f"[BADGE] Template: '{template.name}' (Tenant: {template.tenant_id})")
            
            template_dict = {
                "id": template.id,
                "name": template.name,
                "description": template.description,
                "template_content": template.template_content,
                "logo_url": template.logo_url,
                "logo_public_id": template.logo_public_id,
                "background_url": template.background_url,
                "background_public_id": template.background_public_id,
                "enable_qr_code": template.enable_qr_code,
                "badge_size": template.badge_size,
                "orientation": template.orientation,
                "contact_phone": template.contact_phone,
                "website_url": template.website_url,
                "avatar_url": template.avatar_url,
                "include_avatar": template.include_avatar,
                "created_at": template.created_at.isoformat() if template.created_at else None,
                "updated_at": template.updated_at.isoformat() if template.updated_at else None
            }
            template_list.append(template_dict)
        
        print(f"[BADGE] Total templates found for tenant {tenant.slug}: {len(template_list)}")
        return {"templates": template_list}
    except Exception as e:
        print(f"Error loading badge templates: {e}")
        return {"templates": []}

@router.post("/", response_model=BadgeTemplate)
def create_badge_template(
    *,
    db: Session = Depends(get_db),
    template_in: BadgeTemplateCreate,
    current_user: User = Depends(get_current_active_user),
    tenant_slug: str = Depends(get_tenant_context),
) -> BadgeTemplate:
    """
    Create new badge template for the current tenant.
    """
    # Get tenant ID from slug
    tenant = db.query(Tenant).filter(Tenant.slug == tenant_slug).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    
    # Add tenant_id to the template data
    template_data = template_in.dict()
    template_data['tenant_id'] = tenant.id
    template_create = BadgeTemplateCreate(**template_data)
    
    template = badge_template.create(db=db, obj_in=template_create)
    
    print("=== BADGE TEMPLATE CREATED IN DB ===")
    print(f"Template ID: {template.id}")
    print(f"Template Name: {template.name}")
    print(f"Tenant ID: {template.tenant_id}")
    print("=== END TEMPLATE CONTENT ===")
    
    return template

@router.get("/{template_id}", response_model=BadgeTemplate)
def get_badge_template(
    *,
    db: Session = Depends(get_db),
    template_id: int,
    current_user: User = Depends(get_current_active_user),
    tenant_slug: str = Depends(get_tenant_context),
) -> BadgeTemplate:
    """
    Get badge template by ID for the current tenant.
    """
    # Get tenant ID from slug
    tenant = db.query(Tenant).filter(Tenant.slug == tenant_slug).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    
    template = badge_template.get(db=db, id=template_id)
    if not template or template.tenant_id != tenant.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Template not found"
        )
    return template

@router.put("/{template_id}", response_model=BadgeTemplate)
def update_badge_template(
    *,
    db: Session = Depends(get_db),
    template_id: int,
    template_in: BadgeTemplateUpdate,
    current_user: User = Depends(get_current_active_user),
    tenant_slug: str = Depends(get_tenant_context),
) -> BadgeTemplate:
    """
    Update badge template for the current tenant.
    """
    # Get tenant ID from slug
    tenant = db.query(Tenant).filter(Tenant.slug == tenant_slug).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    
    template = badge_template.get(db=db, id=template_id)
    if not template or template.tenant_id != tenant.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Template not found"
        )
    
    template = badge_template.update(db=db, db_obj=template, obj_in=template_in)
    
    print("=== BADGE TEMPLATE UPDATED IN DB ===")
    print(f"Template ID: {template.id}")
    print(f"Template Name: {template.name}")
    print(f"Tenant ID: {template.tenant_id}")
    print("=== END TEMPLATE UPDATE ===")
    
    return template

@router.delete("/{template_id}")
def delete_badge_template(
    *,
    db: Session = Depends(get_db),
    template_id: int,
    current_user: User = Depends(get_current_active_user),
    tenant_slug: str = Depends(get_tenant_context),
) -> dict:
    """
    Delete badge template for the current tenant.
    """
    from app.models.badge_template import BadgeTemplate
    from app.models.event_badge import EventBadge
    from app.models.participant_badge import ParticipantBadge
    
    # Get tenant ID from slug
    tenant = db.query(Tenant).filter(Tenant.slug == tenant_slug).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    
    template = badge_template.get(db=db, id=template_id)
    if not template or template.tenant_id != tenant.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Template not found"
        )
    
    try:
        # Get all event badges using this template
        event_badge_ids = [eb.id for eb in db.query(EventBadge).filter(EventBadge.badge_template_id == template_id).all()]
        
        # Delete participant badges for these event badges
        if event_badge_ids:
            db.query(ParticipantBadge).filter(ParticipantBadge.event_badge_id.in_(event_badge_ids)).delete(synchronize_session=False)
        
        # Delete event badges
        db.query(EventBadge).filter(EventBadge.badge_template_id == template_id).delete(synchronize_session=False)
        
        # Delete the template
        db.query(BadgeTemplate).filter(BadgeTemplate.id == template_id).delete(synchronize_session=False)
        
        db.commit()
        return {"message": "Template deleted successfully"}
        
    except Exception as e:
        db.rollback()
        print(f"Delete error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete template"
        )

@router.get("/active/list", response_model=List[BadgeTemplate])
def get_active_badge_templates(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    tenant_slug: str = Depends(get_tenant_context),
) -> List[BadgeTemplate]:
    """
    Get all active badge templates for the current tenant.
    """
    # Get tenant ID from slug
    tenant = db.query(Tenant).filter(Tenant.slug == tenant_slug).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    
    return badge_template.get_active_by_tenant(db, tenant_id=tenant.id)

@router.get("/generate/{template_id}/participant/{participant_id}")
def generate_participant_badge(
    template_id: int,
    participant_id: int,
    db: Session = Depends(get_db)
):
    """Generate HTML badge for a participant using template"""
    from fastapi.responses import HTMLResponse
    import re
    from datetime import datetime
    
    # Get the badge template
    template = badge_template.get(db=db, id=template_id)
    if not template:
        raise HTTPException(status_code=404, detail="Badge template not found")
    
    # Get participant
    participant = db.query(EventParticipant).filter(EventParticipant.id == participant_id).first()
    if not participant:
        raise HTTPException(status_code=404, detail="Participant not found")
    
    # Get event details and badge tagline from event certificates
    from app.models.event import Event
    from app.models.event_certificate import EventCertificate
    event = db.query(Event).filter(Event.id == participant.event_id).first()
    
    # Get badge tagline from event certificates
    badge_tagline = ""  # Default empty
    event_certificate = db.query(EventCertificate).filter(
        EventCertificate.event_id == participant.event_id
    ).first()
    
    if event_certificate and event_certificate.template_variables:
        # Check for badge tagline in template variables
        if 'badgeTagline' in event_certificate.template_variables:
            badge_tagline = event_certificate.template_variables['badgeTagline']
        elif 'badge_tagline' in event_certificate.template_variables:
            badge_tagline = event_certificate.template_variables['badge_tagline']
    
    # Create variable mapping for template replacement
    variables = {
        'participantName': participant.full_name,
        'participant_name': participant.full_name,
        'participantRole': (participant.participant_role or participant.role or 'VISITOR').upper(),
        'participant_role': (participant.participant_role or participant.role or 'VISITOR').upper(),
        'eventTitle': event.title if event else '',
        'event_title': event.title if event else '',
        'eventLocation': event.location if event else '',
        'event_location': event.location if event else '',
        'startDate': event.start_date.strftime('%B %d, %Y') if event and event.start_date else '',
        'event_start_date': event.start_date.strftime('%B %d, %Y') if event and event.start_date else '',
        'endDate': event.end_date.strftime('%B %d, %Y') if event and event.end_date else '',
        'event_end_date': event.end_date.strftime('%B %d, %Y') if event and event.end_date else '',
        'badgeTagline': badge_tagline,
        'badge_tagline': badge_tagline
    }
    
    # Start with template HTML
    html_content = template.template_content or ''
    
    # Add logo if available
    if template.logo_url:
        logo_html = f'<img src="{template.logo_url}" alt="Logo" style="max-height: 80px; max-width: 100px; object-fit: contain;" />'
        html_content = html_content.replace('{{logo}}', logo_html)
        html_content = html_content.replace('{{logoUrl}}', template.logo_url)
    else:
        # Remove logo placeholder if no logo
        html_content = html_content.replace('{{logo}}', '')
    
    # Handle participant avatar based on template settings
    if template.include_avatar and template.avatar_url:
        # Use the exact same structure and classes as the template
        avatar_html = f'<img src="{template.avatar_url}" alt="Avatar" class="avatar" />'
        html_content = html_content.replace('{{participantAvatar}}', avatar_html)
    else:
        # Remove avatar placeholder if not included or no avatar URL
        html_content = html_content.replace('{{participantAvatar}}', '')
    
    # Replace template variables
    for key, value in variables.items():
        pattern = f'{{{{\\s*{key}\\s*}}}}'
        html_content = re.sub(pattern, str(value), html_content, flags=re.IGNORECASE)
    
    # Ensure responsive design and proper viewport
    if '<head>' in html_content and '<meta name="viewport"' not in html_content:
        html_content = html_content.replace('<head>', '<head>\n  <meta name="viewport" content="width=device-width, initial-scale=1.0">')
    
    # Enhanced print styles using template's exact specifications
    enhanced_styles = f'''
        <style>
            @media screen {{
                body {{ 
                    margin: 0; 
                    padding: 20px; 
                    background: #f5f5f5;
                    display: flex;
                    justify-content: center;
                    align-items: center;
                    min-height: 100vh;
                    font-family: Arial, sans-serif;
                }}
                .badge {{
                    box-shadow: 0 8px 32px rgba(0,0,0,0.1);
                    transform: scale(1);
                    transition: transform 0.3s ease;
                }}
                .badge:hover {{
                    transform: scale(1.02);
                }}
            }}
            @media print {{
                body {{ 
                    margin: 0; 
                    padding: 0;
                    background: white;
                }}
                @page {{ 
                    size: {template.badge_size or 'A4'}; 
                    margin: 0.5in;
                    orientation: {template.orientation or 'portrait'};
                }}
                .badge {{ 
                    page-break-inside: avoid;
                    box-shadow: none;
                    transform: none;
                }}
            }}
            @media (max-width: 480px) {{
                body {{ padding: 10px; }}
                .badge {{
                    transform: scale(0.8);
                    margin: 10px auto;
                }}
            }}
        </style>
    '''
    
    # Add print functionality
    print_script = '''
        <script>
            function printBadge() {
                window.print();
            }
            
            // Add print button for screen view
            window.onload = function() {
                if (window.matchMedia && !window.matchMedia('print').matches) {
                    const printBtn = document.createElement('button');
                    printBtn.innerHTML = '🖨️ Print Badge';
                    printBtn.style.cssText = `
                        position: fixed;
                        top: 20px;
                        right: 20px;
                        background: #dc2626;
                        color: white;
                        border: none;
                        padding: 12px 20px;
                        border-radius: 8px;
                        cursor: pointer;
                        font-size: 14px;
                        font-weight: bold;
                        box-shadow: 0 4px 12px rgba(220, 38, 38, 0.3);
                        z-index: 1000;
                        transition: all 0.3s ease;
                    `;
                    printBtn.onmouseover = function() {
                        this.style.background = '#b91c1c';
                        this.style.transform = 'translateY(-2px)';
                    };
                    printBtn.onmouseout = function() {
                        this.style.background = '#dc2626';
                        this.style.transform = 'translateY(0)';
                    };
                    printBtn.onclick = printBadge;
                    document.body.appendChild(printBtn);
                }
            };
        </script>
    '''
    
    # Insert enhanced styles and script before closing head tag
    if '</head>' in html_content:
        html_content = html_content.replace('</head>', enhanced_styles + print_script + '</head>')
    else:
        # If no head tag, add it
        html_content = f'<head>{enhanced_styles}{print_script}</head>' + html_content
    
    return HTMLResponse(content=html_content)
