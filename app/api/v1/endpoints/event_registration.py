# File: app/api/v1/endpoints/event_registration.py
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Any
from app.db.database import get_db
from app.models.event import Event
from app.models.event_participant import EventParticipant
from app.models.user import User
from pydantic import BaseModel
import os
from datetime import datetime
from app.core.email_service import email_service
from app.core.config import settings

router = APIRouter()

class EventRegistrationRequest(BaseModel):
    event_id: int
    user_email: str
    full_name: str
    role: str = "attendee"
    
    def dict(self, **kwargs):
        data = super().dict(**kwargs)
        print(f"📝 API: EventRegistrationRequest validation passed: {data}")
        return data

class ParticipantStatusUpdate(BaseModel):
    status: str  # selected, not_selected, waiting, canceled
    notes: str = None

@router.post("/register")
async def register_for_event(
    registration: EventRegistrationRequest,
    db: Session = Depends(get_db)
):
    """Allow users to register for events"""
    
    print(f"🎯 API: Received registration request")
    print(f"   Event ID: {registration.event_id}")
    print(f"   Email: {registration.user_email}")
    print(f"   Name: {registration.full_name}")
    print(f"   Role: {registration.role}")
    print(f"🎯 Full request data: {registration.dict()}")
    
    # Check if event exists
    event = db.query(Event).filter(Event.id == registration.event_id).first()
    if not event:
        print(f"❌ Event {registration.event_id} not found")
        raise HTTPException(status_code=404, detail="Event not found")
    
    print(f"📅 Event found: {event.title} (Status: {event.status})")
    
    # Allow facilitator registration regardless of event status, but restrict attendee registration
    if registration.role != "facilitator" and event.status != "Published":
        print(f"❌ Event not published for attendee registration. Role: {registration.role}, Status: {event.status}")
        raise HTTPException(status_code=400, detail="Registration is only allowed for published events")
    
    # Check if user already registered with same role
    existing = db.query(EventParticipant).filter(
        EventParticipant.event_id == registration.event_id,
        EventParticipant.email == registration.user_email,
        EventParticipant.role == registration.role
    ).first()
    
    if existing:
        print(f"❌ User {registration.user_email} already registered as {registration.role} for event {registration.event_id}")
        raise HTTPException(status_code=400, detail=f"Already registered as {registration.role} for this event")
    
    # Get user if exists
    user = db.query(User).filter(User.email == registration.user_email).first()
    
    print(f"✅ Creating participant for {registration.full_name} as {registration.role}")
    
    try:
        # Create registration with default status as 'registered' and participant_role as 'visitor'
        participant = EventParticipant(
            event_id=registration.event_id,
            email=registration.user_email,
            full_name=registration.full_name,
            role=registration.role,
            participant_role="visitor",  # Default role for all participants
            status="registered",  # Default status when visitor registers
            invited_by=registration.user_email
        )
        
        db.add(participant)
        db.commit()
        db.refresh(participant)
        
        print(f"✅ Participant created successfully with ID: {participant.id}")
        
        # Send facilitator notification email
        if registration.role == "facilitator":
            print(f"📧 Sending facilitator notification email to {registration.user_email}")
            await send_facilitator_notification(participant, db)
        
        return {"message": "Successfully registered for event", "participant_id": participant.id}
        
    except Exception as e:
        print(f"❌ Error creating participant: {str(e)}")
        db.rollback()
        raise HTTPException(status_code=400, detail=f"Failed to register participant: {str(e)}")

@router.get("/event/{event_id}/registrations")
async def get_event_registrations(
    event_id: int,
    status_filter: str = Query(None, description="Filter by status: registered, selected, not_selected, waiting, canceled, attended"),
    db: Session = Depends(get_db)
):
    """Get all registrations for an event with detailed registration data"""
    print(f"\n🔥🔥🔥 EVENT REGISTRATIONS ENDPOINT HIT - EVENT ID: {event_id} 🔥🔥🔥")
    print(f"📊 Status filter: {status_filter}")
    from sqlalchemy import text
    
    # Query participants with detailed registration data
    query = """
    SELECT 
        ep.id, ep.email, ep.full_name, ep.role, ep.status, ep.invited_by, ep.created_at, ep.updated_at,
        ep.country, ep.travelling_from_country, ep.position, ep.project, ep.gender, ep.participant_role,
        ep.decline_reason, ep.declined_at,
        pr.first_name, pr.last_name, pr.oc, pr.contract_status, pr.contract_type,
        pr.gender_identity, pr.sex, pr.pronouns, pr.current_position,
        pr.country_of_work, pr.project_of_work, pr.personal_email, pr.msf_email,
        pr.hrco_email, pr.career_manager_email, pr.line_manager_email, pr.phone_number,
        pr.dietary_requirements, pr.accommodation_needs, pr.certificate_name,
        pr.badge_name, pr.motivation_letter,
        pr.code_of_conduct_confirm, pr.travel_requirements_confirm,
        pr.travelling_internationally, pr.travelling_from_country as pr_travelling_from_country, pr.accommodation_type, pr.daily_meals
    FROM event_participants ep
    LEFT JOIN public_registrations pr ON ep.id = pr.participant_id
    WHERE ep.event_id = :event_id
    """
    
    if status_filter:
        query += " AND ep.status = :status_filter"
    
    params = {"event_id": event_id}
    if status_filter:
        params["status_filter"] = status_filter
    
    result = db.execute(text(query), params)
    participants = result.fetchall()
    
    print(f"📊 Found {len(participants)} participants for event {event_id}")
    for i, p in enumerate(participants[:3]):  # Print first 3 participants
        print(f"👤 Participant {i+1}: ID={p.id}, Name={p.full_name}, Email={p.email}, Status={p.status}, Role={p.role}")
    if len(participants) > 3:
        print(f"👥 ... and {len(participants) - 3} more participants")
    
    result = []
    for p in participants:
        # Data privacy: anonymize personal data for not_selected participants
        if p.status == "not_selected":
            result.append({
                "id": p.id,
                "email": "[REDACTED]",
                "full_name": p.full_name,  # Keep name for audit purposes
                "role": p.role,
                "participant_role": "[REDACTED]",
                "status": p.status,
                "registration_type": "self",
                "registered_by": "[REDACTED]",
                "notes": None,
                "created_at": p.created_at,
                "invitation_sent": False,
                "invitation_sent_at": None,
                "invitation_accepted": False,
                "invitation_accepted_at": None,
                # Redacted registration form data
                "oc": "[REDACTED]",
                "position": "[REDACTED]",
                "country": "[REDACTED]",
                "contract_status": "[REDACTED]",
                "contract_type": "[REDACTED]",
                "gender_identity": "[REDACTED]",
                "sex": "[REDACTED]",
                "pronouns": "[REDACTED]",
                "project_of_work": "[REDACTED]",
                "personal_email": "[REDACTED]",
                "msf_email": "[REDACTED]",
                "hrco_email": "[REDACTED]",
                "career_manager_email": "[REDACTED]",
                "line_manager_email": "[REDACTED]",
                "phone_number": "[REDACTED]",
                "dietary_requirements": "[REDACTED]",
                "accommodation_needs": "[REDACTED]",
                "certificate_name": "[REDACTED]",
                "badge_name": "[REDACTED]",
                "motivation_letter": "[REDACTED]",
                "code_of_conduct_confirm": "[REDACTED]",
                "travel_requirements_confirm": "[REDACTED]",
                "travelling_internationally": "[REDACTED]",
                "accommodation_type": "[REDACTED]",
                "daily_meals": "[REDACTED]",
                "decline_reason": "[REDACTED]",
                "declined_at": "[REDACTED]"
            })
        else:
            result.append({
                "id": p.id,
                "email": p.email,
                "full_name": p.full_name,
                "role": p.role,
                "participant_role": p.participant_role or 'visitor',
                "status": p.status,
                "registration_type": "self",
                "registered_by": p.invited_by,
                "notes": None,
                "created_at": p.created_at,
                "invitation_sent": p.status == "selected" and p.email and p.email.strip(),
                "invitation_sent_at": p.updated_at if p.status == "selected" and p.email and p.email.strip() else None,
                "invitation_accepted": p.status == "confirmed",
                "invitation_accepted_at": p.updated_at if p.status == "confirmed" else None,
                # Registration form data
                "oc": p.oc,
                "position": p.current_position or p.position,
                "country": p.country_of_work or p.country,
                "travelling_from_country": p.pr_travelling_from_country or p.travelling_from_country,
                "contract_status": p.contract_status,
                "contract_type": p.contract_type,
                "gender_identity": p.gender_identity,
                "sex": p.sex,
                "pronouns": p.pronouns,
                "project_of_work": p.project_of_work or p.project,
                "personal_email": p.personal_email,
                "msf_email": p.msf_email,
                "hrco_email": p.hrco_email,
                "career_manager_email": p.career_manager_email,
                "line_manager_email": p.line_manager_email,
                "phone_number": p.phone_number,
                "dietary_requirements": p.dietary_requirements,
                "accommodation_needs": p.accommodation_needs,
                "certificate_name": p.certificate_name,
                "badge_name": p.badge_name,
                "motivation_letter": p.motivation_letter,
                "code_of_conduct_confirm": p.code_of_conduct_confirm,
                "travel_requirements_confirm": p.travel_requirements_confirm,
                "travelling_internationally": p.travelling_internationally,
                "accommodation_type": p.accommodation_type,
                "daily_meals": p.daily_meals,
                "decline_reason": p.decline_reason,
                "declined_at": p.declined_at.isoformat() if p.declined_at else None
            })
    
    return result

@router.get("/participant/{participant_id}")
async def get_participant_details(
    participant_id: int,
    db: Session = Depends(get_db)
):
    """Get detailed information for a specific participant"""
    
    try:
        from sqlalchemy import text
        
        print(f"🔥 BASIC DEBUG: Getting participant details for ID: {participant_id}")
        
        # Get participant with registration details
        result = db.execute(
            text("""
                SELECT 
                    ep.id, ep.email, ep.full_name, ep.role, ep.status, ep.invited_by, 
                    ep.created_at, ep.updated_at, ep.country, ep.travelling_from_country, ep.position, ep.project, 
                    ep.gender, ep.eta, ep.requires_eta, ep.passport_document, ep.ticket_document,
                    ep.dietary_requirements, ep.accommodation_type, ep.participant_name, ep.participant_email,
                    ep.decline_reason, ep.declined_at,
                    pr.travelling_internationally, pr.accommodation_needs, pr.daily_meals,
                    pr.certificate_name, pr.code_of_conduct_confirm, pr.travel_requirements_confirm,
                    pr.phone_number, pr.accommodation_type as pr_accommodation_type
                FROM event_participants ep
                LEFT JOIN public_registrations pr ON ep.id = pr.participant_id
                WHERE ep.id = :participant_id
            """),
            {"participant_id": participant_id}
        ).fetchone()
        
        print(f"🔥 BASIC DEBUG: Query result found: {result is not None}")
        if result:
            print(f"🔥 BASIC DEBUG: Participant data:")
            print(f"🔥 BASIC DEBUG: ID = {result.id}")
            print(f"🔥 BASIC DEBUG: Name = {result.full_name}")
            print(f"🔥 BASIC DEBUG: Email = {result.email}")
            print(f"🔥 BASIC DEBUG: EP Accommodation Type = {result.accommodation_type}")
            print(f"🔥 BASIC DEBUG: PR Accommodation Type = {result.pr_accommodation_type if hasattr(result, 'pr_accommodation_type') else 'N/A'}")
            print(f"🔥 BASIC DEBUG: Travelling Internationally = {result.travelling_internationally}")
            print(f"🔥 BASIC DEBUG: Travelling From Country (EP) = {result.travelling_from_country}")
            print(f"🔥 BASIC DEBUG: Dietary Requirements (EP) = {result.dietary_requirements}")
            print(f"🔥 BASIC DEBUG: Certificate Name = {result.certificate_name}")
            print(f"🔥 BASIC DEBUG: Phone Number = {result.phone_number}")
        
        # Also check if public_registrations record exists separately
        pr_check = db.execute(
            text("SELECT * FROM public_registrations WHERE participant_id = :participant_id"),
            {"participant_id": participant_id}
        ).fetchone()
        
        print(f"🔥 BASIC DEBUG: Public registration record exists: {pr_check is not None}")
        if pr_check:
            print(f"🔥 BASIC DEBUG: Public registration data:")
            print(f"🔥 BASIC DEBUG: First Name = {pr_check.first_name}")
            print(f"🔥 BASIC DEBUG: Last Name = {pr_check.last_name}")
            print(f"🔥 BASIC DEBUG: Travelling Internationally = {pr_check.travelling_internationally}")
            print(f"🔥 BASIC DEBUG: Travelling From Country (PR) = {pr_check.travelling_from_country}")
            print(f"🔥 BASIC DEBUG: Accommodation Type = {pr_check.accommodation_type}")
            print(f"🔥 BASIC DEBUG: Dietary Requirements = {pr_check.dietary_requirements}")
        
        if not result:
            raise HTTPException(status_code=404, detail="Participant not found")
        
        # Get user details if available
        user = None
        try:
            user = db.query(User).filter(User.email == result.email).first()
        except Exception as e:
            print(f"Error fetching user details for {result.email}: {e}")
        
        # Use public_registrations data if available, otherwise fall back to event_participants
        accommodation_type = None
        if hasattr(result, 'pr_accommodation_type') and result.pr_accommodation_type and result.pr_accommodation_type.strip():
            accommodation_type = result.pr_accommodation_type
        elif result.accommodation_type and result.accommodation_type.strip():
            accommodation_type = result.accommodation_type
        
        response_data = {
            "id": result.id,
            "email": result.email,
            "full_name": result.full_name,
            "phone": result.phone_number or (user.phone_number if user and hasattr(user, 'phone_number') else None),
            "role": result.role,
            "status": result.status,
            "registration_type": "self",
            "registered_by": result.invited_by,
            "created_at": result.created_at.isoformat() if result.created_at else None,
            "updated_at": result.updated_at.isoformat() if result.updated_at else None,
            "invitation_sent": result.status == "selected" and result.email and result.email.strip(),
            "invitation_sent_at": result.updated_at.isoformat() if result.status == "selected" and result.email and result.email.strip() and result.updated_at else None,
            "invitation_accepted": result.status == "confirmed",
            "invitation_accepted_at": result.updated_at.isoformat() if result.status == "confirmed" and result.updated_at else None,
            # Registration details from event_participants
            "country": result.country,
            "travelling_from_country": result.travelling_from_country,
            "position": result.position,
            "department": result.project,  # project field stores department
            "gender": result.gender,
            "eta": result.eta,
            "requires_eta": result.requires_eta,
            "passport_document": bool(result.passport_document),
            "ticket_document": bool(result.ticket_document),
            "dietary_requirements": result.dietary_requirements,
            "accommodation_type": accommodation_type,
            # Registration details from public_registrations
            "travelling_internationally": result.travelling_internationally if result.travelling_internationally and result.travelling_internationally.strip() else None,
            "accommodation_needs": result.accommodation_needs if result.accommodation_needs and result.accommodation_needs.strip() else None,
            "daily_meals": result.daily_meals if result.daily_meals and result.daily_meals.strip() else None,
            "certificate_name": result.certificate_name if result.certificate_name and result.certificate_name.strip() else None,
            "code_of_conduct_confirm": result.code_of_conduct_confirm if result.code_of_conduct_confirm and result.code_of_conduct_confirm.strip() else None,
            "travel_requirements_confirm": result.travel_requirements_confirm if result.travel_requirements_confirm and result.travel_requirements_confirm.strip() else None,
            "decline_reason": result.decline_reason,
            "declined_at": result.declined_at.isoformat() if result.declined_at else None
        }
        
        print(f"🔥 BASIC DEBUG: Final response data:")
        print(f"🔥 BASIC DEBUG: Accommodation Type = {response_data['accommodation_type']}")
        print(f"🔥 BASIC DEBUG: Travelling Internationally = {response_data['travelling_internationally']}")
        print(f"🔥 BASIC DEBUG: Travelling From Country = {response_data['travelling_from_country']}")
        print(f"🔥 BASIC DEBUG: Raw DB travelling_from_country = {result.travelling_from_country}")
        print(f"🔥 BASIC DEBUG: Dietary Requirements = {response_data['dietary_requirements']}")
        print(f"🔥 BASIC DEBUG: Certificate Name = {response_data['certificate_name']}")
        
        return response_data
    except HTTPException:
        raise
    except Exception as e:
        print(f"🔥 BASIC DEBUG: EXCEPTION in get_participant_details: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.put("/participant/{participant_id}/status")
async def update_participant_status(
    participant_id: int,
    status_update: ParticipantStatusUpdate,
    db: Session = Depends(get_db)
):
    """Update participant status (admin only)"""
    
    participant = db.query(EventParticipant).filter(
        EventParticipant.id == participant_id
    ).first()
    
    if not participant:
        raise HTTPException(status_code=404, detail="Participant not found")
    
    # Validate status
    valid_statuses = ["registered", "selected", "not_selected", "waiting", "canceled", "attended"]
    if status_update.status not in valid_statuses:
        raise HTTPException(status_code=400, detail="Invalid status")
    
    participant.status = status_update.status
    # Notes field not available yet
    
    # If status is selected, send invitation email and push notification
    if status_update.status == "selected":
        print(f"🎉 SENDING SELECTION EMAIL to {participant.full_name} ({participant.email})")
        email_sent = await send_status_notification(participant, status_update.status, db)
        if email_sent:
            print(f"✅ SELECTION EMAIL SENT SUCCESSFULLY to {participant.email}")
        else:
            print(f"❌ FAILED TO SEND SELECTION EMAIL to {participant.email}")
        
        # Auto-allocate drink vouchers to selected participants
        try:
            print(f"🍻 AUTO-ALLOCATING VOUCHERS for participant {participant.id} in event {participant.event_id}")
            success = await auto_allocate_vouchers_to_participant(participant, db)
            if success:
                print(f"✅ AUTO-ALLOCATION SUCCESSFUL for participant {participant.id}")
            else:
                print(f"❌ AUTO-ALLOCATION FAILED for participant {participant.id}")
        except Exception as e:
            print(f"❌ ERROR AUTO-ALLOCATING VOUCHERS: {str(e)}")
            import traceback
            traceback.print_exc()
        
        # Send push notification
        try:
            from app.services.firebase_service import firebase_service
            event = db.query(Event).filter(Event.id == participant.event_id).first()
            if event:
                push_sent = firebase_service.send_to_user(
                    db=db,
                    user_email=participant.email,
                    title="🎉 You've been selected!",
                    body=f"Congratulations! You've been selected for {event.title}",
                    data={
                        "type": "event_selection",
                        "event_id": str(event.id),
                        "participant_id": str(participant.id)
                    }
                )
                if push_sent:
                    print(f"✅ PUSH NOTIFICATION SENT to {participant.email}")
                else:
                    print(f"❌ FAILED TO SEND PUSH NOTIFICATION to {participant.email}")
        except Exception as e:
            print(f"❌ ERROR SENDING PUSH NOTIFICATION: {str(e)}")
            
        # participant.invitation_sent = True
        # participant.invitation_sent_at = datetime.utcnow()
    elif status_update.status == "not_selected":
        print(f"😔 SENDING REJECTION EMAIL to {participant.full_name} ({participant.email})")
        email_sent = await send_status_notification(participant, status_update.status, db)
        if email_sent:
            print(f"✅ REJECTION EMAIL SENT SUCCESSFULLY to {participant.email}")
        else:
            print(f"❌ FAILED TO SEND REJECTION EMAIL to {participant.email}")
        
        # Send push notification for rejection
        try:
            from app.services.firebase_service import firebase_service
            event = db.query(Event).filter(Event.id == participant.event_id).first()
            if event:
                push_sent = firebase_service.send_to_user(
                    db=db,
                    user_email=participant.email,
                    title="Event Application Update",
                    body=f"Thank you for your interest in {event.title}. Unfortunately, we were unable to select you at this time.",
                    data={
                        "type": "event_rejection",
                        "event_id": str(event.id),
                        "participant_id": str(participant.id)
                    }
                )
                if push_sent:
                    print(f"✅ PUSH NOTIFICATION SENT to {participant.email}")
                else:
                    print(f"❌ FAILED TO SEND PUSH NOTIFICATION to {participant.email}")
        except Exception as e:
            print(f"❌ ERROR SENDING PUSH NOTIFICATION: {str(e)}")
        
        # Data privacy: Ensure not_selected participants are not created as system users
        try:
            user = db.query(User).filter(User.email == participant.email).first()
            if user and user.role in ['VISITOR', 'GUEST'] and user.auto_registered:
                print(f"🗑️ REMOVING AUTO-REGISTERED USER for not_selected participant: {participant.email}")
                db.delete(user)
                print(f"✅ AUTO-REGISTERED USER REMOVED: {participant.email}")
        except Exception as e:
            print(f"❌ ERROR REMOVING AUTO-REGISTERED USER: {str(e)}")
    
    try:
        db.commit()
    except Exception as e:
        db.rollback()
        print(f"❌ ERROR COMMITTING STATUS UPDATE: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to update participant status")
    
    return {"message": "Participant status updated successfully"}

@router.get("/user/{user_email}/registrations")
async def get_user_registrations(
    user_email: str,
    db: Session = Depends(get_db)
):
    """Get all event registrations for a user"""
    
    participants = db.query(EventParticipant).filter(
        EventParticipant.email == user_email
    ).all()
    
    result = []
    for p in participants:
        event = db.query(Event).filter(Event.id == p.event_id).first()
        result.append({
            "participant_id": p.id,
            "event": {
                "id": event.id,
                "title": event.title,
                "start_date": event.start_date,
                "end_date": event.end_date,
                "location": event.location
            },
            "status": p.status,
            "registered_at": p.created_at
        })
    
    return result

async def send_facilitator_notification(participant, db):
    """Send email notification to facilitators when added to event"""
    try:
        # Check if participant has a valid email
        if not participant.email or not participant.email.strip():
            print(f"No email address for facilitator {participant.full_name}, skipping email notification")
            return False
        
        # Get event details
        event = db.query(Event).filter(Event.id == participant.event_id).first()
        if not event:
            print(f"Event not found for facilitator {participant.full_name}")
            return False
        
        subject = f"🎯 You've been added as facilitator for {event.title}"
        
        message = f"""
        <p>Dear {participant.full_name},</p>
        <p>You have been added as a <strong>facilitator</strong> for the upcoming event <strong>{event.title}</strong>.</p>
        
        <div style="margin: 20px 0; padding: 20px; background-color: #e8f5e8; border-left: 4px solid #22c55e;">
            <h3>Event Details:</h3>
            <p><strong>Event:</strong> {event.title}</p>
            <p><strong>Location:</strong> {event.location}</p>
            <p><strong>Date:</strong> {event.start_date.strftime('%B %d, %Y')} - {event.end_date.strftime('%B %d, %Y')}</p>
            <p><strong>Your Role:</strong> Facilitator</p>
        </div>
        
        <div style="margin: 20px 0; padding: 20px; background-color: #f0f9ff; border-left: 4px solid #3b82f6;">
            <h3>Next Steps:</h3>
            <ol>
                <li><strong>Download the Msafiri mobile app</strong></li>
                <li><strong>Login using your work email</strong> ({participant.email})</li>
                <li><strong>Access event details</strong> and prepare your materials</li>
                <li><strong>Submit any required documents</strong> through the mobile app</li>
            </ol>
        </div>
        
        <p><strong>Important:</strong> As a facilitator, please use the Msafiri mobile application to access detailed event information and coordinate with other facilitators.</p>
        
        <p>We look forward to your contribution to this event!</p>
        """
        
        # Use the existing email service
        success = email_service.send_notification_email(
            to_email=participant.email,
            user_name=participant.full_name,
            title=subject,
            message=message
        )
        return success
        
    except Exception as e:
        print(f"Error sending facilitator notification email: {e}")
        return False

async def auto_allocate_vouchers_to_participant(participant, db):
    """Automatically allocate drink vouchers to selected participants"""
    try:
        from sqlalchemy import text
        
        # Check if there are existing voucher allocations for this event
        existing_check = db.execute(
            text("SELECT COUNT(*) FROM event_allocations WHERE event_id = :event_id AND drink_vouchers_per_participant > 0"),
            {"event_id": participant.event_id}
        ).scalar()
        
        if existing_check > 0:
            print(f"✅ VOUCHERS ALREADY ALLOCATED for event {participant.event_id}")
            return True
        
        # Get event details for tenant_id
        event = db.query(Event).filter(Event.id == participant.event_id).first()
        if not event:
            print(f"❌ EVENT NOT FOUND for participant {participant.id}")
            return False
        
        # Create automatic voucher allocation (2 vouchers per participant) using raw SQL
        db.execute(
            text("""
                INSERT INTO event_allocations (
                    event_id, inventory_item_id, quantity_per_participant, 
                    drink_vouchers_per_participant, notes, status, tenant_id, 
                    created_by, approved_by, approved_at, created_at
                ) VALUES (
                    :event_id, NULL, 0, 2, 
                    'AUTO_ALLOCATED|NOTES:Automatically allocated to selected participants',
                    'approved', :tenant_id, 'system', 'system', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
                )
            """),
            {
                "event_id": participant.event_id,
                "tenant_id": event.tenant_id
            }
        )
        
        db.commit()
        print(f"✅ AUTO-ALLOCATED 2 DRINK VOUCHERS for event {participant.event_id}")
        return True
        
    except Exception as e:
        print(f"❌ ERROR AUTO-ALLOCATING VOUCHERS: {str(e)}")
        db.rollback()
        return False

async def send_status_notification(participant, status, db):
    """Send email notification based on participant status"""
    try:
        # Check if participant has a valid email
        if not participant.email or not participant.email.strip():
            print(f"No email address for participant {participant.full_name}, skipping email notification")
            return False
        
        # Get event details
        event = db.query(Event).filter(Event.id == participant.event_id).first()
        if not event:
            print(f"Event not found for participant {participant.full_name}")
            return False
        
        if status == "selected":
            subject = f"🎉 You've been selected for {event.title}!"
            
            message = f"""
            <p>Dear {participant.full_name},</p>
            <p>We're excited to inform you that you have been selected to participate in <strong>{event.title}</strong>.</p>
            
            <div style="margin: 20px 0; padding: 20px; background-color: #e8f5e8; border-left: 4px solid #22c55e;">
                <h3>Event Details:</h3>
                <p><strong>Event:</strong> {event.title}</p>
                <p><strong>Location:</strong> {event.location}</p>
                <p><strong>Date:</strong> {event.start_date.strftime('%B %d, %Y')} - {event.end_date.strftime('%B %d, %Y')}</p>
            </div>
            
            <div style="margin: 20px 0; padding: 20px; background-color: #f0f9ff; border-left: 4px solid #3b82f6;">
                <h3>Next Steps:</h3>
                <ol>
                    <li><strong>Download the Msafiri mobile app</strong></li>
                    <li><strong>Login using your work email</strong> ({participant.email})</li>
                    <li><strong>Accept the invitation</strong> from the app notifications</li>
                    <li><strong>Submit required documents</strong> through the mobile app</li>
                </ol>
            </div>
            
            <p><strong>Important:</strong> Please use the Msafiri mobile application to accept your invitation and access all event details.</p>
            
            <p>We look forward to your participation!</p>
            """
            
        elif status == "not_selected":
            subject = f"Event Application Update - {event.title}"
            message = f"""
            <p>Dear {participant.full_name},</p>
            <p>Thank you for registering for <strong>{event.title}</strong>. Unfortunately, we were unable to select you for participation at this time due to limited capacity.</p>
            
            <div style="margin: 20px 0; padding: 20px; background-color: #fef3c7; border-left: 4px solid #f59e0b;">
                <p><strong>Event:</strong> {event.title}</p>
                <p><strong>Location:</strong> {event.location}</p>
                <p><strong>Date:</strong> {event.start_date.strftime('%B %d, %Y')} - {event.end_date.strftime('%B %d, %Y')}</p>
            </div>
            
            <p>We encourage you to:</p>
            <ul>
                <li>Keep an eye out for future events</li>
                <li>Stay connected with us for upcoming opportunities</li>
            </ul>
            
            <p>Thank you for your understanding.</p>
            """
        else:
            return False  # No email for other statuses
        
        # Use the existing email service
        success = email_service.send_notification_email(
            to_email=participant.email,
            user_name=participant.full_name,
            title=subject,
            message=message
        )
        return success
        
    except Exception as e:
        print(f"Error sending notification email: {e}")
        return False



@router.get("/event/{event_id}/stats")
async def get_event_participant_stats(
    event_id: int,
    db: Session = Depends(get_db)
):
    """Get participant statistics for an event (excluding facilitators)"""
    
    # Get all participants excluding facilitators
    participants = db.query(EventParticipant).filter(
        EventParticipant.event_id == event_id,
        EventParticipant.role != "facilitator"
    ).all()
    
    # Get facilitators separately
    facilitators = db.query(EventParticipant).filter(
        EventParticipant.event_id == event_id,
        EventParticipant.role == "facilitator"
    ).all()
    
    total_registered = len(participants)
    selected_count = len([p for p in participants if p.status == "selected"])
    
    return {
        "total_registered": total_registered,
        "selected_count": selected_count,
        "waiting_count": len([p for p in participants if p.status == "waiting"]),
        "not_selected_count": len([p for p in participants if p.status == "not_selected"]),
        "attended_count": len([p for p in participants if p.status == "attended"]),
        "canceled_count": len([p for p in participants if p.status == "canceled"]),
        "facilitator_count": len(facilitators)
    }

@router.post("/participant/{participant_id}/resend-invitation")
async def resend_invitation(
    participant_id: int,
    db: Session = Depends(get_db)
):
    """Resend invitation email to selected participant"""
    
    participant = db.query(EventParticipant).filter(
        EventParticipant.id == participant_id
    ).first()
    
    if not participant:
        raise HTTPException(status_code=404, detail="Participant not found")
    
    if participant.status != "selected":
        raise HTTPException(status_code=400, detail="Can only resend invitations to selected participants")
    
    # Send invitation email
    print(f"🔄 RESENDING INVITATION to {participant.full_name} ({participant.email})")
    email_sent = await send_status_notification(participant, "selected", db)
    
    if email_sent:
        print(f"✅ INVITATION EMAIL SENT SUCCESSFULLY to {participant.email}")
    else:
        print(f"❌ FAILED TO SEND INVITATION EMAIL to {participant.email}")
    
    # Also resend push notification
    try:
        from app.services.firebase_service import firebase_service
        event = db.query(Event).filter(Event.id == participant.event_id).first()
        if event:
            push_sent = firebase_service.send_to_user(
                db=db,
                user_email=participant.email,
                title="🎉 You've been selected!",
                body=f"Congratulations! You've been selected for {event.title}",
                data={
                    "type": "event_selection",
                    "event_id": str(event.id),
                    "participant_id": str(participant.id)
                }
            )
            if push_sent:
                print(f"✅ PUSH NOTIFICATION RESENT to {participant.email}")
            else:
                print(f"❌ FAILED TO RESEND PUSH NOTIFICATION to {participant.email}")
    except Exception as e:
        print(f"❌ ERROR RESENDING PUSH NOTIFICATION: {str(e)}")
    
    # Update invitation tracking (temporarily disabled)
    # participant.invitation_sent = True
    # participant.invitation_sent_at = datetime.utcnow()
    db.commit()
    
    return {"message": "Invitation resent successfully", "email_sent": email_sent}

@router.post("/participant/{participant_id}/accept-invitation")
async def accept_invitation(
    participant_id: int,
    db: Session = Depends(get_db)
):
    """Accept invitation (called from confirmation link)"""
    
    participant = db.query(EventParticipant).filter(
        EventParticipant.id == participant_id
    ).first()
    
    if not participant:
        raise HTTPException(status_code=404, detail="Participant not found")
    
    if participant.status != "selected":
        raise HTTPException(status_code=400, detail="Only selected participants can accept invitations")
    
    # Update acceptance status (temporarily disabled)
    # participant.invitation_accepted = True
    # participant.invitation_accepted_at = datetime.utcnow()
    participant.status = "confirmed"
    db.commit()
    
    return {"message": "Invitation accepted successfully"}

@router.delete("/participant/{participant_id}")
async def delete_participant(
    participant_id: int,
    db: Session = Depends(get_db)
):
    """Delete a participant from an event"""
    
    print(f"🗑️ DELETE PARTICIPANT REQUEST: ID={participant_id}")
    
    participant = db.query(EventParticipant).filter(
        EventParticipant.id == participant_id
    ).first()
    
    if not participant:
        print(f"❌ PARTICIPANT NOT FOUND: ID={participant_id}")
        raise HTTPException(status_code=404, detail="Participant not found")
    
    print(f"✅ PARTICIPANT FOUND: ID={participant.id}, Name={participant.full_name}, Email={participant.email}")
    
    try:
        from sqlalchemy import text
        
        print(f"🗑️ COMPREHENSIVE DELETION for participant {participant_id} ({participant.email})")
        
        # Delete all related records in correct order to avoid foreign key constraints
        tables_to_clean = [
            ("public_registrations", "participant_id", participant_id),
            ("accommodation_allocations", "participant_id", participant_id),
            ("participant_qr_codes", "participant_id", participant_id),
            ("event_allocations", "created_by", participant.email),
            ("notifications", "user_email", participant.email),
            ("user_fcm_tokens", "user_email", participant.email),
        ]
        
        for table_name, column_name, value in tables_to_clean:
            try:
                # Check count first
                count_result = db.execute(
                    text(f"SELECT COUNT(*) FROM {table_name} WHERE {column_name} = :value"),
                    {"value": value}
                )
                count = count_result.scalar()
                
                if count > 0:
                    print(f"🗑️ DELETING {count} records from {table_name}")
                    db.execute(
                        text(f"DELETE FROM {table_name} WHERE {column_name} = :value"),
                        {"value": value}
                    )
                    db.commit()  # Commit each deletion separately
                    print(f"✅ DELETED {count} records from {table_name}")
                else:
                    print(f"ℹ️ No records found in {table_name}")
                    
            except Exception as e:
                print(f"⚠️ Could not clean {table_name}: {e}")
                db.rollback()  # Rollback failed operation
        
        # Final verification - check if there are still any foreign key references
        print(f"🔍 FINAL VERIFICATION before deleting participant")
        try:
            remaining_aa = db.execute(
                text("SELECT COUNT(*) FROM accommodation_allocations WHERE participant_id = :participant_id"),
                {"participant_id": participant_id}
            ).scalar()
            print(f"📊 Remaining accommodation allocations: {remaining_aa}")
            
            if remaining_aa > 0:
                print(f"⚠️ FORCE DELETING remaining accommodation allocations")
                db.execute(
                    text("DELETE FROM accommodation_allocations WHERE participant_id = :participant_id"),
                    {"participant_id": participant_id}
                )
                db.commit()
                print(f"✅ FORCE DELETED remaining accommodation allocations")
                
        except Exception as e:
            print(f"⚠️ Error in final verification: {e}")
            db.rollback()
        
        # Now delete the participant
        print(f"🗑️ DELETING PARTICIPANT: ID={participant_id}")
        db.delete(participant)
        db.commit()
        
        print(f"✅ PARTICIPANT DELETED SUCCESSFULLY: ID={participant_id}")
        return {"message": "Participant and all related data deleted successfully"}
        
    except Exception as e:
        db.rollback()
        print(f"❌ ERROR DELETING PARTICIPANT: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Failed to delete participant: {str(e)}")

@router.post("/user/update-fcm-token")
async def update_fcm_token(
    token_data: dict,
    db: Session = Depends(get_db)
) -> Any:
    """Update user's FCM token for push notifications"""
    
    user_email = token_data.get('email')
    fcm_token = token_data.get('fcm_token')
    
    if not user_email or not fcm_token:
        raise HTTPException(status_code=400, detail="Email and FCM token are required")
    
    user = db.query(User).filter(User.email == user_email).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    user.fcm_token = fcm_token
    db.commit()
    
    return {"message": "FCM token updated successfully"}