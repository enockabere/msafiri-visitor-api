from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app.db.database import get_db
from app.api.deps import get_current_user, get_tenant_context
from app.models.user import User
from app.models.tenant import Tenant
from app.models.event import Event
from app.models.event_participant import EventParticipant
from app.models.event_certificate import EventCertificate, ParticipantCertificate
from app.models.event_badge import EventBadge, ParticipantBadge
from app.models.certificate_template import CertificateTemplate
from app.models.badge_template import BadgeTemplate
from app.schemas.event_certificate import EventCertificateCreate, EventCertificateUpdate, EventCertificateResponse, ParticipantCertificateResponse
from app.schemas.event_badge import EventBadgeCreate, EventBadgeUpdate, EventBadgeResponse, ParticipantBadgeResponse
import qrcode
from io import BytesIO
import base64
import os

router = APIRouter()

@router.get("/{event_id}/certificates", response_model=List[EventCertificateResponse])
def get_event_certificates(
    event_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_slug: str = Depends(get_tenant_context)
):
    """Get all certificates for an event"""
    tenant = db.query(Tenant).filter(Tenant.slug == tenant_slug).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    
    # Verify event exists and belongs to tenant
    event = db.query(Event).filter(
        Event.id == event_id,
        Event.tenant_id == tenant.id
    ).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    
    # Get certificates
    certificates = db.query(EventCertificate).filter(
        EventCertificate.event_id == event_id,
        EventCertificate.tenant_id == tenant.id
    ).all()
    
    return certificates

@router.post("/{event_id}/certificates", response_model=EventCertificateResponse)
def create_event_certificate(
    event_id: int,
    certificate_data: EventCertificateCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_slug: str = Depends(get_tenant_context)
):
    """Create a certificate for an event"""
    tenant = db.query(Tenant).filter(Tenant.slug == tenant_slug).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    
    # Verify event exists and belongs to tenant
    event = db.query(Event).filter(
        Event.id == event_id,
        Event.tenant_id == tenant.id
    ).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    
    # Get certificate template
    template = db.query(CertificateTemplate).filter(
        CertificateTemplate.id == certificate_data.certificate_template_id
    ).first()
    if not template:
        raise HTTPException(status_code=404, detail="Certificate template not found")
    
    # Create event certificate
    event_certificate = EventCertificate(
        event_id=event_id,
        certificate_template_id=certificate_data.certificate_template_id,
        template_variables=certificate_data.template_variables,
        tenant_id=tenant.id,
        created_by=current_user.id
    )
    
    db.add(event_certificate)
    db.commit()
    db.refresh(event_certificate)
    
    # Create participant certificates for all event participants
    participants = db.query(EventParticipant).filter(EventParticipant.event_id == event_id).all()
    
    for participant in participants:
        participant_cert = ParticipantCertificate(
            event_certificate_id=event_certificate.id,
            participant_id=participant.id
        )
        db.add(participant_cert)
    
    db.commit()
    
    return event_certificate

@router.get("/{event_id}/certificates/{certificate_id}", response_model=EventCertificateResponse)
def get_event_certificate(
    event_id: int,
    certificate_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_slug: str = Depends(get_tenant_context)
):
    """Get a specific event certificate"""
    tenant = db.query(Tenant).filter(Tenant.slug == tenant_slug).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    
    certificate = db.query(EventCertificate).filter(
        EventCertificate.id == certificate_id,
        EventCertificate.event_id == event_id,
        EventCertificate.tenant_id == tenant.id
    ).first()
    
    if not certificate:
        raise HTTPException(status_code=404, detail="Certificate not found")
    
    return certificate

@router.put("/{event_id}/certificates/{certificate_id}", response_model=EventCertificateResponse)
def update_event_certificate(
    event_id: int,
    certificate_id: int,
    certificate_data: EventCertificateUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_slug: str = Depends(get_tenant_context)
):
    """Update an event certificate"""
    tenant = db.query(Tenant).filter(Tenant.slug == tenant_slug).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    
    certificate = db.query(EventCertificate).filter(
        EventCertificate.id == certificate_id,
        EventCertificate.event_id == event_id,
        EventCertificate.tenant_id == tenant.id
    ).first()
    
    if not certificate:
        raise HTTPException(status_code=404, detail="Certificate not found")
    
    # Update certificate fields
    update_data = certificate_data.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(certificate, field, value)
    
    db.commit()
    db.refresh(certificate)
    
    return certificate

@router.delete("/{event_id}/certificates/{certificate_id}")
def delete_event_certificate(
    event_id: int,
    certificate_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_slug: str = Depends(get_tenant_context)
):
    """Delete an event certificate or badge"""
    tenant = db.query(Tenant).filter(Tenant.slug == tenant_slug).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    
    # Try to find as certificate first
    certificate = db.query(EventCertificate).filter(
        EventCertificate.id == certificate_id,
        EventCertificate.event_id == event_id,
        EventCertificate.tenant_id == tenant.id
    ).first()
    
    if certificate:
        # Delete associated participant certificates
        db.query(ParticipantCertificate).filter(
            ParticipantCertificate.event_certificate_id == certificate_id
        ).delete()
        
        db.delete(certificate)
        db.commit()
        return {"message": "Certificate deleted successfully"}
    
    # Try to find as badge
    badge = db.query(EventBadge).filter(
        EventBadge.id == certificate_id,
        EventBadge.event_id == event_id,
        EventBadge.tenant_id == tenant.id
    ).first()
    
    if badge:
        # Delete associated participant badges
        db.query(ParticipantBadge).filter(
            ParticipantBadge.event_badge_id == certificate_id
        ).delete()
        
        db.delete(badge)
        db.commit()
        return {"message": "Badge deleted successfully"}
    
    raise HTTPException(status_code=404, detail="Certificate or badge not found")

@router.get("/{event_id}/certificates/{certificate_id}/generate/{participant_id}")
def generate_participant_certificate(
    event_id: int,
    certificate_id: int,
    participant_id: int,
    db: Session = Depends(get_db)
):
    """Generate HTML certificate for a participant using template"""
    import sys
    print("\n" + "="*80, flush=True)
    print(f"[CERT] CERTIFICATE/BADGE GENERATION STARTED", flush=True)
    print(f"   Event ID: {event_id}", flush=True)
    print(f"   Certificate ID: {certificate_id}", flush=True)
    print(f"   Participant ID: {participant_id}", flush=True)
    print("="*80 + "\n", flush=True)
    sys.stdout.flush()
    sys.stderr.flush()

    from fastapi.responses import HTMLResponse
    import json
    import re
    from datetime import datetime

    # Get the event certificate or badge and participant
    print(f"[INFO] Step 1: Fetching event certificate/badge...")
    
    # First try to find it as a certificate
    event_certificate = db.query(EventCertificate).filter(
        EventCertificate.id == certificate_id,
        EventCertificate.event_id == event_id
    ).first()
    
    event_badge = None
    if not event_certificate:
        # Try to find it as a badge
        event_badge = db.query(EventBadge).filter(
            EventBadge.id == certificate_id,
            EventBadge.event_id == event_id
        ).first()
    
    if not event_certificate and not event_badge:
        print(f"[ERROR] ERROR: Event certificate/badge not found!")
        raise HTTPException(status_code=404, detail="Certificate/Badge not found")
    
    # Use whichever one we found
    item = event_certificate or event_badge
    is_badge = event_badge is not None
    
    print(f"[OK] Event {'badge' if is_badge else 'certificate'} found: ID={item.id}")

    print(f"\n[USER] Step 2: Fetching participant...")
    participant = db.query(EventParticipant).filter(
        EventParticipant.id == participant_id,
        EventParticipant.event_id == event_id
    ).first()

    if not participant:
        print(f"[ERROR] ERROR: Participant not found!")
        raise HTTPException(status_code=404, detail="Participant not found")
    print(f"[OK] Participant found: {participant.full_name}")
    
    # Get event details
    print(f"\n[DATE]  Step 3: Fetching event details...")
    event = db.query(Event).filter(Event.id == event_id).first()
    if event:
        print(f"[OK] Event found: {event.title}")
    else:
        print(f"[WARN]  Warning: Event not found")

    # Get certificate template (could be certificate or badge template)
    print(f"\n[DOC] Step 4: Fetching template...")
    
    # Determine if this is a badge or certificate and get template variables
    if is_badge:
        template_vars = event_badge.template_variables or {}
        template_id = event_badge.badge_template_id
        # Get badge template
        template = db.query(BadgeTemplate).filter(
            BadgeTemplate.id == template_id
        ).first()
        template_type = "badge"
    else:
        template_vars = event_certificate.template_variables or {}
        template_id = event_certificate.certificate_template_id
        # Get certificate template
        template = db.query(CertificateTemplate).filter(
            CertificateTemplate.id == template_id
        ).first()
        template_type = "certificate"

    if not template:
        print(f"[ERROR] ERROR: {template_type.title()} template not found!")
        raise HTTPException(status_code=404, detail=f"{template_type.title()} template not found")

    print(f"[OK] {template_type.title()} template found: {template.name}")
    print(f"[IMG]  Template ID: {template.id}")
    print(f"[IMG]  Logo URL: {template.logo_url}")
    print(f"[IMG]  Has Logo: {bool(template.logo_url)}")
    print(f"[IMG]  Template content length: {len(template.template_content) if template.template_content else 0} chars")
    print(f"[IMG]  Template content preview (first 200 chars):")
    print(f"     {template.template_content[:200] if template.template_content else 'EMPTY'}")

    # Get template variables from event certificate/badge
    print(f"\n[VARS] Step 5: Processing template variables...")
    print(f"   Variables count: {len(template_vars)}")
    print(f"   Variables keys: {list(template_vars.keys())}")
    for key, value in template_vars.items():
        value_preview = str(value)[:100] if value else 'None'
        print(f"     - {key}: {value_preview}")
    
    # Create variable mapping for template replacement
    # Note: Frontend sends camelCase field names (organizerName, facilitatorName, etc.)
    # Event data is always pulled from Event model to ensure current information
    variables = {
        'participantName': participant.full_name,
        'participant_name': participant.full_name,
        'eventTitle': event.title if event else (template_vars.get('eventTitle') or ''),
        'event_title': event.title if event else (template_vars.get('eventTitle') or ''),
        'eventLocation': event.location if event else (template_vars.get('eventLocation') or ''),
        'event_location': event.location if event else (template_vars.get('eventLocation') or ''),
        'startDate': event.start_date.strftime('%B %d, %Y') if event and event.start_date else (template_vars.get('startDate') or ''),
        'event_start_date': event.start_date.strftime('%B %d, %Y') if event and event.start_date else (template_vars.get('startDate') or ''),
        'endDate': event.end_date.strftime('%B %d, %Y') if event and event.end_date else (template_vars.get('endDate') or ''),
        'event_end_date': event.end_date.strftime('%B %d, %Y') if event and event.end_date else (template_vars.get('endDate') or ''),
        'eventDateRange': f"{event.start_date.strftime('%B %d')} - {event.end_date.strftime('%B %d, %Y')}" if event and event.start_date and event.end_date else '',
        'event_date_range': f"{event.start_date.strftime('%B %d')} - {event.end_date.strftime('%B %d, %Y')}" if event and event.start_date and event.end_date else '',
        'certificate_id': str(certificate_id),
        'participant_id': str(participant_id),
        'event_id': str(event_id),
        'certificateDate': template_vars.get('certificateDate', datetime.now().strftime('%B %d, %Y')),
    }
    
    # Add badge-specific variables if this is a badge
    if is_badge:
        variables.update({
            'badgeTagline': template_vars.get('badgeTagline', ''),
            'badge_tagline': template_vars.get('badgeTagline', ''),
        })
    else:
        # Add certificate-specific variables
        variables.update({
            # Use correct field names that match frontend (camelCase)
            'organizerName': template_vars.get('organizerName', ''),
            'organizer': template_vars.get('organizerName', ''),  # Fallback for both naming conventions
            'organizerTitle': template_vars.get('organizerTitle', ''),
            'facilitatorName': template_vars.get('facilitatorName', ''),
            'facilitator': template_vars.get('facilitatorName', ''),  # Fallback for both naming conventions
            'facilitatorTitle': template_vars.get('facilitatorTitle', ''),
            'coordinatorName': template_vars.get('coordinatorName', ''),
            'coordinator': template_vars.get('coordinatorName', ''),  # Fallback for both naming conventions
            'coordinatorTitle': template_vars.get('coordinatorTitle', ''),
            'courseDescription': template_vars.get('courseDescription', ''),
            'course_description': template_vars.get('courseDescription', ''),  # Fallback for both naming conventions
            'courseObjectives': template_vars.get('courseObjectives', ''),
            'course_objectives': template_vars.get('courseObjectives', ''),  # Fallback for both naming conventions
            'courseContents': template_vars.get('courseContents', ''),
            'course_contents': template_vars.get('courseContents', ''),  # Fallback for both naming conventions
            'certificateDate': template_vars.get('certificateDate', datetime.now().strftime('%B %d, %Y')),
            'certificate_date': template_vars.get('certificateDate', datetime.now().strftime('%B %d, %Y')),
        })
    # Use template content exactly as stored in database
    html_content = template.template_content or ''

    # Apply dynamic sizing for badges
    if is_badge and hasattr(template, 'badge_size'):
        size_multiplier = {
            'small': 0.75,
            'standard': 1.0,
            'large': 1.25
        }.get(template.badge_size, 1.0)

        base_width = 280
        base_height = 450
        width = int(base_width * size_multiplier)
        height = int(base_height * size_multiplier)
        red_height = int(273 * size_multiplier)
        white_height = int(177 * size_multiplier)

        print(f"[SIZE] Badge size: {template.badge_size}")
        print(f"[SIZE] Dimensions: {width}px x {height}px (multiplier: {size_multiplier}x)")

        html_content = html_content.replace('width: 280px;', f'width: {width}px;')
        html_content = html_content.replace('height: 450px;', f'height: {height}px;')
        html_content = html_content.replace('height: 273px;', f'height: {red_height}px;')
        html_content = html_content.replace('height: 177px;', f'height: {white_height}px;')
        html_content = html_content.replace('top: 273px;', f'top: {red_height}px;')

    # Get all template variables dynamically
    all_variables = template_vars.copy() if template_vars else {}

    # Add participant and event data to variables
    # IMPORTANT: Event data from the Event model takes precedence over stored template_variables
    # This ensures event details are always current even if template_variables weren't saved
    participant_role = participant.participant_role or participant.role or ''
    all_variables.update({
        'eventTitle': event.title if event else (template_vars.get('eventTitle') or ''),
        'startDate': event.start_date.strftime('%B %d, %Y') if event and event.start_date else (template_vars.get('startDate') or ''),
        'endDate': event.end_date.strftime('%B %d, %Y') if event and event.end_date else (template_vars.get('endDate') or ''),
        'eventLocation': event.location if event else (template_vars.get('eventLocation') or ''),
        'participantName': participant.full_name or '',
        'participantRole': participant_role.upper() if participant_role else '',  # Uppercase for badges
        'certificateDate': template_vars.get('certificateDate', datetime.now().strftime('%B %d, %Y')),
    })

    # Handle special placeholders FIRST before general variable replacement
    # For certificates, use larger logo sizes that match typical certificate designs
    if '{{logo}}' in html_content:
        if is_badge:
            # For badges, use smaller logo
            logo_html = f'<img src="{template.logo_url}" alt="Logo" style="max-width: 80px; max-height: 40px; object-fit: contain;" />' if template.logo_url else ''
        else:
            # For certificates, use larger logo to match design templates
            logo_html = f'<img src="{template.logo_url}" alt="Organization Logo" style="max-height: 100px; max-width: 300px; display: block; margin: 0 auto;" />' if template.logo_url else ''
        html_content = html_content.replace('{{logo}}', logo_html)
        print(f"[LOGO] Logo replaced with: {template.logo_url}")

    if '{{participantAvatar}}' in html_content:
        avatar_html = f'<img src="{template.avatar_url}" alt="Avatar" class="avatar" />' if template.avatar_url else ''
        html_content = html_content.replace('{{participantAvatar}}', avatar_html)
        print(f"[BADGE] Avatar replaced with: {template.avatar_url}")

    # Generate QR code for certificates (same URL as generation endpoint)
    if '{{qrCode}}' in html_content or not is_badge:
        # Create public certificate URL
        api_url = os.getenv('NEXT_PUBLIC_API_URL', 'http://localhost:8000')
        cert_url = f"{api_url}/api/v1/events/{event_id}/certificates/{certificate_id}/generate/{participant_id}"

        # Generate QR code
        qr = qrcode.QRCode(version=1, box_size=10, border=2)
        qr.add_data(cert_url)
        qr.make(fit=True)
        qr_img = qr.make_image(fill_color="black", back_color="white")

        # Convert to base64
        buffer = BytesIO()
        qr_img.save(buffer, format='PNG')
        qr_base64 = base64.b64encode(buffer.getvalue()).decode()
        qr_img_tag = f'<img src="data:image/png;base64,{qr_base64}" alt="QR Code" style="width: 80px; height: 80px; object-fit: contain;" />'

        # Replace QR code placeholder
        html_content = html_content.replace('{{qrCode}}', qr_img_tag)
        print(f"[QR] QR code generated for certificate URL: {cert_url}")

    # Generate QR code for badge - ALWAYS if this is a badge
    if is_badge:
        # Create public badge URL using NEW badge-specific endpoint
        api_url = os.getenv('NEXT_PUBLIC_API_URL', 'http://localhost:8000')
        badge_url = f"{api_url}/api/v1/events/{event_id}/badges/{certificate_id}/generate/{participant_id}"

        # Generate QR code
        qr = qrcode.QRCode(version=1, box_size=10, border=2)
        qr.add_data(badge_url)
        qr.make(fit=True)
        qr_img = qr.make_image(fill_color="black", back_color="white")

        # Convert to base64
        buffer = BytesIO()
        qr_img.save(buffer, format='PNG')
        qr_base64 = base64.b64encode(buffer.getvalue()).decode()
        qr_img_tag = f'<img src="data:image/png;base64,{qr_base64}" alt="QR Code" style="width: 100%; height: 100%; object-fit: contain;" />'

        # Replace all possible QR placeholders
        html_content = html_content.replace('{{qrCode}}', qr_img_tag)
        html_content = html_content.replace('>QR</div>', f'>{qr_img_tag}</div>')
        # Also try direct text replacement
        import re
        html_content = re.sub(r'<div class="qr-code">QR</div>', f'<div class="qr-code">{qr_img_tag}</div>', html_content)

        print(f"[QR] QR code generated for URL: {badge_url}")
        print(f"[QR] QR replacements made in HTML")

    # Handle logo watermark placeholder (typically used on second page of certificates)
    if '{{logoWatermark}}' in html_content:
        watermark_html = f'<img src="{template.logo_url}" alt="Watermark" style="max-width: 400px; max-height: 400px;" />' if template.logo_url else ''
        html_content = html_content.replace('{{logoWatermark}}', watermark_html)
        print(f"[LOGO] Logo watermark replaced with: {template.logo_url}")

    # Find all remaining placeholders in the template
    import re
    placeholders = re.findall(r'{{(\w+)}}', html_content)

    # Replace all variables found in template
    print(f"\n[FIND] Step 8: Replacing template variables...")
    print(f"   Variables to replace: {list(all_variables.keys())[:10]}... ({len(all_variables)} total)")
    print(f"   Placeholders found in template: {placeholders[:10]}... ({len(placeholders)} total)")

    for placeholder in placeholders:
        value = all_variables.get(placeholder, '')
        html_content = html_content.replace(f'{{{{{placeholder}}}}}', str(value))
    
    # Handle Handlebars {{#each}} blocks for lists
    # The frontend sends HTML from Rich Text Editor, so we handle both HTML and plain text

    # Replace {{#each courseObjectives}} with actual list items
    objectives = template_vars.get('courseObjectives', '')
    print(f"[FIND] DEBUG: Course objectives raw value: '{objectives[:100] if objectives else 'EMPTY'}'")
    if objectives:
        # Check if it's already HTML or plain text
        if '<li>' in objectives or '<p>' in objectives:
            # Already HTML from Rich Text Editor - use as-is but extract content
            objectives_html = objectives
        else:
            # Plain text - convert to list items
            objectives_html = '\n'.join([f'<li style="margin-bottom: 4px;">{obj.strip()}</li>' for obj in objectives.split('\n') if obj.strip()])
            objectives_html = f'<ul style="font-size: 11px; line-height: 1.6; color: #333; padding-left: 20px;">{objectives_html}</ul>'

        objectives_pattern = r'{{#each courseObjectives}}.*?{{/each}}'
        html_content = re.sub(objectives_pattern, objectives_html, html_content, flags=re.DOTALL | re.IGNORECASE)
        print(f"[FIND] DEBUG: Course objectives pattern replaced")
    else:
        print("[FIND] DEBUG: No course objectives found")

    # Replace {{#each courseContents}} with actual list items
    contents = template_vars.get('courseContents', '')
    print(f"[FIND] DEBUG: Course contents raw value: '{contents[:100] if contents else 'EMPTY'}'")
    if contents:
        # Check if it's already HTML or plain text
        if '<li>' in contents or '<p>' in contents:
            # Already HTML from Rich Text Editor - use as-is
            contents_html = contents
        else:
            # Plain text - convert to list items
            contents_html = '\n'.join([f'<li style="margin-bottom: 4px;">{content.strip()}</li>' for content in contents.split('\n') if content.strip()])
            contents_html = f'<ul style="font-size: 11px; line-height: 1.6; color: #333; padding-left: 20px;">{contents_html}</ul>'

        contents_pattern = r'{{#each courseContents}}.*?{{/each}}'
        html_content = re.sub(contents_pattern, contents_html, html_content, flags=re.DOTALL | re.IGNORECASE)
        print(f"[FIND] DEBUG: Course contents pattern replaced")
    else:
        print("[FIND] DEBUG: No course contents found")
    
    # Add enhanced print styles using template specifications
    if is_badge and hasattr(template, 'badge_size') and hasattr(template, 'orientation'):
        # Use badge template's exact size and orientation
        enhanced_styles = f'''
        <style>
            @media print {{
                @page {{ 
                    size: {template.badge_size or 'A4'}; 
                    margin: 0.5in;
                    orientation: {template.orientation or 'portrait'};
                }}
            }}
        </style>
        '''
    else:
        # Default styles for certificates
        enhanced_styles = '''
        <style>
            @media print {
                @page { margin: 0.5in; }
            }
        </style>
        '''
    
    # Add print styles and auto-print script
    print(f"\n[PRINT] Step 8: Adding print styles and scripts...")
    html_content = html_content.replace('</head>', enhanced_styles + '''
        <script>
            window.onload = function() {
                setTimeout(function() {
                    window.print();
                }, 500);
            };
        </script>
    </head>''')
    
    # Print the complete generated HTML for debugging
    print(f"\n[DEBUG] COMPLETE GENERATED HTML:")
    print("=" * 100)
    print(html_content)
    print("=" * 100)

    print(f"\n" + "="*80)
    print(f"[OK] {template_type.upper()} GENERATION COMPLETE")
    print(f"   Final HTML length: {len(html_content)} chars")
    print(f"   Contains images: {html_content.count('<img')} <img> tags")
    print(f"   Contains Cloudinary URLs: {html_content.count('cloudinary')} references")
    print(f"\n[SEND] Returning HTML response to browser...")
    print("="*80 + "\n")

    # Print a sample of the final HTML to verify logos
    print(f"\n[FIND] FINAL HTML PREVIEW (first 1000 chars):")
    print(html_content[:1000])
    print(f"\n... (truncated, total length: {len(html_content)} chars)")

    # Verify all placeholders have been replaced
    remaining_placeholders = re.findall(r'{{(\w+)}}', html_content)
    if remaining_placeholders:
        print(f"\n[WARN] WARNING: Some placeholders were not replaced: {remaining_placeholders}")
        for placeholder in remaining_placeholders:
            print(f"   - {{{{ {placeholder} }}}} was not found in variables")
    else:
        print(f"\n[OK] All template placeholders successfully replaced")

    return HTMLResponse(content=html_content)

@router.get("/{event_id}/badges/{badge_id}/generate/{participant_id}")
def generate_participant_badge(
    event_id: int,
    badge_id: int,
    participant_id: int,
    db: Session = Depends(get_db)
):
    """Generate HTML badge for a participant using badge template"""
    import sys
    print("\n" + "="*80, flush=True)
    print(f"[BADGE] BADGE GENERATION STARTED", flush=True)
    print(f"   Event ID: {event_id}", flush=True)
    print(f"   Badge ID: {badge_id}", flush=True)
    print(f"   Participant ID: {participant_id}", flush=True)
    print("="*80 + "\n", flush=True)

    from fastapi.responses import HTMLResponse
    import json
    import re
    from datetime import datetime

    # Get the event badge
    print(f"[INFO] Step 1: Fetching event badge...")
    event_badge = db.query(EventBadge).filter(
        EventBadge.id == badge_id,
        EventBadge.event_id == event_id
    ).first()

    if not event_badge:
        print(f"[ERROR] ERROR: Event badge not found!")
        raise HTTPException(status_code=404, detail="Badge not found")

    print(f"[OK] Event badge found: ID={event_badge.id}")

    print(f"\n[USER] Step 2: Fetching participant...")
    participant = db.query(EventParticipant).filter(
        EventParticipant.id == participant_id,
        EventParticipant.event_id == event_id
    ).first()

    if not participant:
        print(f"[ERROR] ERROR: Participant not found!")
        raise HTTPException(status_code=404, detail="Participant not found")
    print(f"[OK] Participant found: {participant.full_name}")

    # Get event details
    print(f"\n[DATE] Step 3: Fetching event details...")
    event = db.query(Event).filter(Event.id == event_id).first()
    if event:
        print(f"[OK] Event found: {event.title}")
    else:
        print(f"[WARN] Warning: Event not found")

    # Get badge template
    print(f"\n[DOC] Step 4: Fetching badge template...")
    template_vars = event_badge.template_variables or {}
    template_id = event_badge.badge_template_id

    template = db.query(BadgeTemplate).filter(
        BadgeTemplate.id == template_id
    ).first()

    if not template:
        print(f"[ERROR] ERROR: Badge template not found!")
        raise HTTPException(status_code=404, detail="Badge template not found")

    print(f"[OK] Badge template found: {template.name}")
    print(f"[IMG] Template ID: {template.id}")
    print(f"[IMG] Logo URL: {template.logo_url}")
    print(f"[IMG] Avatar URL: {template.avatar_url}")

    # Get template variables
    print(f"\n[VARS] Step 5: Processing template variables...")
    print(f"   Variables count: {len(template_vars)}")
    print(f"   Variables keys: {list(template_vars.keys())}")

    # Use template content from database
    html_content = template.template_content or ''

    # Calculate dimensions based on badge size
    size_multiplier = {
        'small': 0.75,
        'standard': 1.0,
        'large': 1.25
    }.get(template.badge_size, 1.0)

    base_width = 280
    base_height = 450
    width = int(base_width * size_multiplier)
    height = int(base_height * size_multiplier)
    red_height = int(273 * size_multiplier)
    white_height = int(177 * size_multiplier)

    print(f"[SIZE] Badge size: {template.badge_size}")
    print(f"[SIZE] Dimensions: {width}px x {height}px (multiplier: {size_multiplier}x)")
    print(f"[SIZE] Red section: {red_height}px, White section: {white_height}px")

    # Replace size values in CSS
    html_content = html_content.replace('width: 280px;', f'width: {width}px;')
    html_content = html_content.replace('height: 450px;', f'height: {height}px;')
    html_content = html_content.replace('height: 273px;', f'height: {red_height}px;')
    html_content = html_content.replace('height: 177px;', f'height: {white_height}px;')
    html_content = html_content.replace('top: 273px;', f'top: {red_height}px;')

    # Add participant and event data to variables
    participant_role = participant.participant_role or participant.role or ''
    all_variables = template_vars.copy() if template_vars else {}
    all_variables.update({
        'eventTitle': event.title or '',
        'startDate': event.start_date.strftime('%B %d, %Y') if event and event.start_date else '',
        'endDate': event.end_date.strftime('%B %d, %Y') if event and event.end_date else '',
        'participantName': participant.full_name or '',
        'participantRole': participant_role.upper() if participant_role else ''
    })

    # Handle logo replacement FIRST
    if '{{logo}}' in html_content:
        logo_html = f'<img src="{template.logo_url}" alt="Logo" style="max-width: 80px; max-height: 40px; object-fit: contain;" />' if template.logo_url else ''
        html_content = html_content.replace('{{logo}}', logo_html)
        print(f"[BADGE] Logo replaced with: {template.logo_url}")

    # Handle avatar replacement
    if '{{participantAvatar}}' in html_content:
        avatar_html = f'<img src="{template.avatar_url}" alt="Avatar" class="avatar" />' if template.avatar_url else ''
        html_content = html_content.replace('{{participantAvatar}}', avatar_html)
        print(f"[BADGE] Avatar replaced with: {template.avatar_url}")

    # Generate QR code for badge with BADGE-SPECIFIC URL
    api_url = os.getenv('NEXT_PUBLIC_API_URL', 'http://localhost:8000')
    badge_url = f"{api_url}/api/v1/events/{event_id}/badges/{badge_id}/generate/{participant_id}"

    # Generate QR code
    qr = qrcode.QRCode(version=1, box_size=10, border=2)
    qr.add_data(badge_url)
    qr.make(fit=True)
    qr_img = qr.make_image(fill_color="black", back_color="white")

    # Convert to base64
    buffer = BytesIO()
    qr_img.save(buffer, format='PNG')
    qr_base64 = base64.b64encode(buffer.getvalue()).decode()
    qr_img_tag = f'<img src="data:image/png;base64,{qr_base64}" alt="QR Code" style="width: 100%; height: 100%; object-fit: contain;" />'

    # Replace all possible QR placeholders
    html_content = html_content.replace('{{qrCode}}', qr_img_tag)
    html_content = html_content.replace('>QR</div>', f'>{qr_img_tag}</div>')
    html_content = re.sub(r'<div class="qr-code">QR</div>', f'<div class="qr-code">{qr_img_tag}</div>', html_content)

    print(f"[QR] QR code generated for badge URL: {badge_url}")

    # Replace all other template variables
    placeholders = re.findall(r'{{(\w+)}}', html_content)
    for placeholder in placeholders:
        value = all_variables.get(placeholder, '')
        html_content = html_content.replace(f'{{{{{placeholder}}}}}', str(value))

    # Add print styles
    enhanced_styles = f'''
    <style>
        @media print {{
            @page {{
                size: {template.badge_size or 'standard'};
                margin: 0.5in;
                orientation: {template.orientation or 'portrait'};
            }}
        }}
    </style>
    '''

    html_content = html_content.replace('</head>', enhanced_styles + '''
        <script>
            window.onload = function() {
                setTimeout(function() {
                    window.print();
                }, 500);
            };
        </script>
    </head>''')

    print(f"\n[OK] BADGE GENERATION COMPLETE")
    print(f"   Badge URL: {badge_url}")
    print("="*80 + "\n")

    return HTMLResponse(content=html_content)

@router.post("/{event_id}/certificates/{certificate_id}/assign-participants")
def assign_participants_to_certificate(
    event_id: int,
    certificate_id: int,
    db: Session = Depends(get_db)
):
    """Manually assign all event participants to an existing certificate"""
    # Get the event certificate
    event_certificate = db.query(EventCertificate).filter(
        EventCertificate.id == certificate_id,
        EventCertificate.event_id == event_id
    ).first()
    
    if not event_certificate:
        raise HTTPException(status_code=404, detail="Event certificate not found")
    
    # Get all participants for this event
    participants = db.query(EventParticipant).filter(EventParticipant.event_id == event_id).all()
    
    # Delete existing participant certificates for this event certificate
    db.query(ParticipantCertificate).filter(
        ParticipantCertificate.event_certificate_id == certificate_id
    ).delete()
    
    # Create new participant certificates
    created_count = 0
    for participant in participants:
        participant_cert = ParticipantCertificate(
            event_certificate_id=certificate_id,
            participant_id=participant.id
        )
        db.add(participant_cert)
        created_count += 1
    
    db.commit()
    
    return {
        "message": f"Successfully assigned {created_count} participants to certificate",
        "participants_assigned": created_count
    }

@router.get("/{event_id}/certificates/participant/{participant_id}", response_model=ParticipantCertificateResponse)
def get_event_participant_certificate(
    event_id: int,
    participant_id: int,
    db: Session = Depends(get_db)
):
    """Get certificate for a specific participant in an event"""
    # Debug: Check what certificates exist for this event
    event_certificates = db.query(EventCertificate).filter(EventCertificate.event_id == event_id).all()
    print(f"[FIND] DEBUG: Found {len(event_certificates)} event certificates for event {event_id}")
    
    for cert in event_certificates:
        print(f"[INFO] Event Certificate ID: {cert.id}, Template ID: {cert.certificate_template_id}")
        
        # Check participant certificates for this event certificate
        participant_certs = db.query(ParticipantCertificate).filter(
            ParticipantCertificate.event_certificate_id == cert.id
        ).all()
        print(f" Found {len(participant_certs)} participant certificates for event cert {cert.id}")
        
        for pc in participant_certs:
            print(f"   - Participant ID: {pc.participant_id}")
    
    # Get participant certificate through event certificate
    participant_cert = db.query(ParticipantCertificate).join(EventCertificate).filter(
        ParticipantCertificate.participant_id == participant_id,
        EventCertificate.event_id == event_id
    ).first()
    
    print(f"[CERT] Looking for participant {participant_id} in event {event_id}")
    print(f"[OK] Found participant certificate: {participant_cert is not None}")
    
    # If no participant certificate found, but event certificates exist, auto-assign
    if not participant_cert and event_certificates:
        print(f"[AUTO] No participant certificate found, attempting auto-assignment...")
        
        # Verify participant exists in this event
        participant = db.query(EventParticipant).filter(
            EventParticipant.id == participant_id,
            EventParticipant.event_id == event_id
        ).first()
        
        if participant:
            print(f"[AUTO] Participant {participant_id} exists in event {event_id}, creating certificate...")
            
            # Create participant certificate for the first available event certificate
            first_cert = event_certificates[0]
            participant_cert = ParticipantCertificate(
                event_certificate_id=first_cert.id,
                participant_id=participant_id
            )
            db.add(participant_cert)
            db.commit()
            db.refresh(participant_cert)
            
            print(f"[AUTO] Created participant certificate: Event Cert {first_cert.id} -> Participant {participant_id}")
        else:
            print(f"[AUTO] Participant {participant_id} not found in event {event_id}")
    
    if not participant_cert:
        raise HTTPException(status_code=404, detail="Certificate not found for participant")
    
    return participant_cert

@router.get("/participants/{participant_id}/certificate", response_model=ParticipantCertificateResponse)
def get_participant_certificate(
    participant_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_slug: str = Depends(get_tenant_context)
):
    """Get certificate for a specific participant"""
    tenant = db.query(Tenant).filter(Tenant.slug == tenant_slug).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    
    # Verify participant exists and belongs to tenant
    participant = db.query(EventParticipant).join(Event).filter(
        EventParticipant.id == participant_id,
        Event.tenant_id == tenant.id
    ).first()
    if not participant:
        raise HTTPException(status_code=404, detail="Participant not found")
    
    participant_cert = db.query(ParticipantCertificate).filter(
        ParticipantCertificate.participant_id == participant_id
    ).first()
    
    if not participant_cert:
        raise HTTPException(status_code=404, detail="Certificate not found for participant")
    
    return participant_cert
