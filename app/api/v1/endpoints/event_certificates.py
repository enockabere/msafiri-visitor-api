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
from app.models.certificate_template import CertificateTemplate
from app.schemas.event_certificate import EventCertificateCreate, EventCertificateUpdate, EventCertificateResponse, ParticipantCertificateResponse

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
    
    # Verify certificate template exists and belongs to tenant
    template = db.query(CertificateTemplate).filter(
        CertificateTemplate.id == certificate_data.certificate_template_id,
        CertificateTemplate.tenant_id == tenant.id
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
    """Delete an event certificate"""
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
    
    # Delete associated participant certificates
    db.query(ParticipantCertificate).filter(
        ParticipantCertificate.event_certificate_id == certificate_id
    ).delete()
    
    db.delete(certificate)
    db.commit()
    
    return {"message": "Certificate deleted successfully"}

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
    print(f"[CERT] CERTIFICATE GENERATION STARTED", flush=True)
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

    # Get the event certificate and participant
    print(f"[INFO] Step 1: Fetching event certificate...")
    event_certificate = db.query(EventCertificate).filter(
        EventCertificate.id == certificate_id,
        EventCertificate.event_id == event_id
    ).first()

    if not event_certificate:
        print(f"[ERROR] ERROR: Event certificate not found!")
        raise HTTPException(status_code=404, detail="Certificate not found")
    print(f"[OK] Event certificate found: ID={event_certificate.id}")

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

    # Get certificate template
    print(f"\n[DOC] Step 4: Fetching certificate template...")
    template = db.query(CertificateTemplate).filter(
        CertificateTemplate.id == event_certificate.certificate_template_id
    ).first()

    if not template:
        print(f"[ERROR] ERROR: Certificate template not found!")
        raise HTTPException(status_code=404, detail="Certificate template not found")

    print(f"[OK] Template found: {template.name}")
    print(f"[IMG]  Template ID: {template.id}")
    print(f"[IMG]  Logo URL: {template.logo_url}")
    print(f"[IMG]  Has Logo: {bool(template.logo_url)}")
    print(f"[IMG]  Template content length: {len(template.template_content) if template.template_content else 0} chars")
    print(f"[IMG]  Template content preview (first 200 chars):")
    print(f"     {template.template_content[:200] if template.template_content else 'EMPTY'}")

    # Get template variables from event certificate
    print(f"\n[VARS] Step 5: Processing template variables...")
    template_vars = event_certificate.template_variables or {}
    print(f"   Variables count: {len(template_vars)}")
    print(f"   Variables keys: {list(template_vars.keys())}")
    for key, value in template_vars.items():
        value_preview = str(value)[:100] if value else 'None'
        print(f"     - {key}: {value_preview}")
    
    # Create variable mapping for template replacement
    # Note: Frontend sends camelCase field names (organizerName, facilitatorName, etc.)
    variables = {
        'participantName': participant.full_name,
        'participant_name': participant.full_name,
        'eventTitle': event.title if event else '',
        'event_title': event.title if event else '',
        'eventLocation': event.location if event else '',
        'event_location': event.location if event else '',
        'startDate': event.start_date.strftime('%B %d, %Y') if event and event.start_date else '',
        'event_start_date': event.start_date.strftime('%B %d, %Y') if event and event.start_date else '',
        'endDate': event.end_date.strftime('%B %d, %Y') if event and event.end_date else '',
        'event_end_date': event.end_date.strftime('%B %d, %Y') if event and event.end_date else '',
        'eventDateRange': f"{event.start_date.strftime('%B %d')} - {event.end_date.strftime('%B %d, %Y')}" if event and event.start_date and event.end_date else '',
        'event_date_range': f"{event.start_date.strftime('%B %d')} - {event.end_date.strftime('%B %d, %Y')}" if event and event.start_date and event.end_date else '',
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
        'certificate_id': str(certificate_id),
        'participant_id': str(participant_id),
        'event_id': str(event_id)
    }
    
    # Start with template HTML
    print(f"\n[STYLE] Step 6: Processing HTML template...")
    html_content = template.template_content or ''
    print(f"   Initial HTML length: {len(html_content)} chars")

    # Ensure template has proper HTML structure
    html_has_doctype = html_content.strip().startswith('<!DOCTYPE html>')
    html_has_html_tag = html_content.strip().startswith('<html')
    print(f"   Has DOCTYPE: {html_has_doctype}")
    print(f"   Has <html> tag: {html_has_html_tag}")

    if not html_has_doctype and not html_has_html_tag:
        print(f"   [WARN]  Template missing HTML structure, wrapping it...")
        html_content = f'''<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8">
  <title>Certificate</title>
</head>
<body>
{html_content}
</body>
</html>'''
        print(f"   [OK] HTML structure added, new length: {len(html_content)} chars")

    has_logo_placeholder = '{{logo}}' in html_content
    has_watermark_placeholder = '{{logoWatermark}}' in html_content
    print(f"\n[FIND] Placeholder check:")
    print(f"   Contains {{{{logo}}}}: {has_logo_placeholder}")
    print(f"   Contains {{{{logoWatermark}}}}: {has_watermark_placeholder}")

    # Add logo if available
    if template.logo_url:
        print(f"\n[IMG]  Step 7: INJECTING LOGOS...")
        print(f"   Logo URL: {template.logo_url}")

        # Logo for page 1 (top of certificate)
        logo_html = f'<img src="{template.logo_url}" alt="Logo" style="max-width: 200px; height: auto;" />'
        # Watermark logo for page 2 (large, faded background)
        watermark_html = f'<img src="{template.logo_url}" alt="Watermark" style="max-width: 450px; height: auto;" />'

        print(f"   Generated logo HTML: {logo_html}")
        print(f"   Generated watermark HTML: {watermark_html[:100]}...")

        # Replace placeholders if they exist
        if has_logo_placeholder:
            print(f"   [OK] Replacing {{{{logo}}}} placeholder...")
            html_content = html_content.replace('{{logo}}', logo_html)
            print(f"   [OK] Logo placeholder replaced!")
        else:
            print(f"   [WARN]  No {{{{logo}}}} placeholder found, injecting manually...")
            # Inject logo at the beginning of the first content div/section
            import re
            # Find first div with style (likely the certificate container)
            first_div_match = re.search(r'(<div[^>]*>)', html_content)
            if first_div_match:
                insert_pos = first_div_match.end()
                print(f"   Found first <div> at position {insert_pos}")
                html_content = html_content[:insert_pos] + f'\n  <div style="text-align: center; margin-bottom: 20px;">{logo_html}</div>\n  ' + html_content[insert_pos:]
                print(f"   [OK] Logo injected after first <div>!")
            else:
                print(f"   [ERROR] Could not find first <div> to inject logo!")

        if '{{logoUrl}}' in html_content:
            print(f"   Replacing {{{{logoUrl}}}} placeholder...")
            html_content = html_content.replace('{{logoUrl}}', template.logo_url)

        # Always try to replace watermark placeholder
        if '{{logoWatermark}}' in html_content:
            print(f"   [OK] Replacing {{{{logoWatermark}}}} placeholder...")
            html_content = html_content.replace('{{logoWatermark}}', watermark_html)
            print(f"   [OK] Watermark placeholder replaced!")
        elif has_watermark_placeholder:
            print(f"   [WARN]  Watermark placeholder found but replacement failed, trying regex...")
            import re
            html_content = re.sub(r'\{\{\s*logoWatermark\s*\}\}', watermark_html, html_content, flags=re.IGNORECASE)
            print(f"   [OK] Watermark replaced via regex!")
        else:
            print(f"   [WARN]  No {{{{logoWatermark}}}} placeholder found, checking for page break...")
            # Inject watermark on page 2 - look for page break
            if 'page-break-before: always' in html_content:
                print(f"   Found page break, injecting watermark on page 2...")
                # Find the div after the page break
                page_break_pattern = r'(<div style="page-break-before: always;"></div>\s*<div[^>]*>)'
                page2_match = re.search(page_break_pattern, html_content)
                if page2_match:
                    # Insert watermark after the opening div of page 2
                    insert_pos = page2_match.end()
                    print(f"   Found page 2 div at position {insert_pos}")
                    watermark_div = f'\n  <div style="position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%); opacity: 0.1; z-index: 0;">{watermark_html}</div>\n  '
                    html_content = html_content[:insert_pos] + watermark_div + html_content[insert_pos:]
                    print(f"   [OK] Watermark injected on page 2!")
                else:
                    print(f"   [ERROR] Could not find page 2 div to inject watermark!")
            else:
                print(f"   [WARN]  No page break found, cannot inject watermark!")

        img_count = html_content.count('<img')
        cloudinary_count = html_content.count('cloudinary')
        print(f"\n[STATS] Final logo check:")
        print(f"   Number of <img> tags: {img_count}")
        print(f"   Number of 'cloudinary' references: {cloudinary_count}")
        print(f"   Final HTML length: {len(html_content)} chars")

        if img_count == 0:
            print(f"   [ERROR] WARNING: NO IMAGES IN FINAL HTML!")
        else:
            print(f"   [OK] Images successfully added to HTML!")

    else:
        print(f"\n[WARN]  Step 7: NO LOGO URL - Removing placeholders...")
        # If no logo, remove placeholders
        html_content = html_content.replace('{{logo}}', '')
        html_content = html_content.replace('{{logoUrl}}', '')
        html_content = html_content.replace('{{logoWatermark}}', '')
    
    # Final check and force replacement of logo placeholders if they still exist
    if template.logo_url:
        if '{{logo}}' in html_content:
            print(f"[WARN]  WARNING: {{{{logo}}}} still in content after replacement, forcing replacement...")
            html_content = html_content.replace('{{logo}}', logo_html)
        if '{{logoWatermark}}' in html_content:
            print(f"[WARN]  WARNING: {{{{logoWatermark}}}} still in content after replacement, forcing replacement...")
            html_content = html_content.replace('{{logoWatermark}}', watermark_html)

    # Replace Handlebars-style variables {{variable_name}}
    print(f"\n[FIND] Step 8: Replacing template variables...")
    print(f"   Variables to replace: {list(variables.keys())[:10]}... ({len(variables)} total)")
    for key, value in variables.items():
        pattern = f'{{{{\\s*{key}\\s*}}}}'
        if re.search(pattern, html_content, flags=re.IGNORECASE):
            html_content = re.sub(pattern, str(value), html_content, flags=re.IGNORECASE)
        else:
            pass  # Variable not in template
    
    # Handle Handlebars {{#each}} blocks for lists
    # Replace {{#each courseObjectives}} with actual list items
    objectives = template_vars.get('courseObjectives', '')
    print(f"[FIND] DEBUG: Course objectives: '{objectives}'")
    if objectives:
        objectives_html = '\n'.join([f'<li>{obj.strip()}</li>' for obj in objectives.split('\n') if obj.strip()])
        objectives_pattern = r'{{#each courseObjectives}}.*?{{/each}}'
        print(f"[FIND] DEBUG: Objectives HTML: {objectives_html}")
        html_content = re.sub(objectives_pattern, f'<ul>{objectives_html}</ul>', html_content, flags=re.DOTALL | re.IGNORECASE)
    else:
        print("[FIND] DEBUG: No course objectives found")

    # Replace {{#each courseContents}} with actual list items
    contents = template_vars.get('courseContents', '')
    print(f"[FIND] DEBUG: Course contents: '{contents}'")
    if contents:
        contents_html = '\n'.join([f'<li>{content.strip()}</li>' for content in contents.split('\n') if content.strip()])
        contents_pattern = r'{{#each courseContents}}.*?{{/each}}'
        print(f"[FIND] DEBUG: Contents HTML: {contents_html}")
        html_content = re.sub(contents_pattern, f'<ul>{contents_html}</ul>', html_content, flags=re.DOTALL | re.IGNORECASE)
    else:
        print("[FIND] DEBUG: No course contents found")
    
    # Add print styles and auto-print script
    print(f"\n[PRINT]  Step 8: Adding print styles and scripts...")
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

    print(f"\n" + "="*80)
    print(f"[OK] CERTIFICATE GENERATION COMPLETE")
    print(f"   Final HTML length: {len(html_content)} chars")
    print(f"   Contains images: {html_content.count('<img')} <img> tags")
    print(f"   Contains Cloudinary URLs: {html_content.count('cloudinary')} references")
    print(f"\n[SEND] Returning HTML response to browser...")
    print("="*80 + "\n")

    # Print a sample of the final HTML to verify logos
    print(f"\n[FIND] FINAL HTML PREVIEW (first 1000 chars):")
    print(html_content[:1000])
    print(f"\n... (truncated, total length: {len(html_content)} chars)")

    # FINAL EMERGENCY FIX: Force replace any remaining logo placeholders
    print(f"\n>>> CHECKPOINT: About to check for watermark placeholder...")
    print(f">>> Has logo_url: {bool(template.logo_url)}")
    print(f">>> logoWatermark in content: {'{{logoWatermark}}' in html_content}")

    if template.logo_url:
        if '{{logoWatermark}}' in html_content:
            emergency_watermark = f'<img src="{template.logo_url}" alt="Watermark" style="max-width: 450px; height: auto;" />'
            print(f">>> Before replace, content has logoWatermark: {'{{logoWatermark}}' in html_content}")
            html_content = html_content.replace('{{logoWatermark}}', emergency_watermark)
            print(f">>> After replace, content has logoWatermark: {'{{logoWatermark}}' in html_content}")
            print(f"\n[WARN] EMERGENCY: Forced watermark replacement at final stage!")
        else:
            print(f">>> Watermark placeholder NOT FOUND in content!")
    else:
        print(f">>> No logo_url, skipping watermark replacement")

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