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
        # Create registration with default status as 'registered'
        participant = EventParticipant(
            event_id=registration.event_id,
            email=registration.user_email,
            full_name=registration.full_name,
            role=registration.role,
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
    from sqlalchemy import text
    
    # Query participants with detailed registration data
    query = """
    SELECT 
        ep.id, ep.email, ep.full_name, ep.role, ep.status, ep.invited_by, ep.created_at, ep.updated_at,
        ep.country, ep.position, ep.project, ep.gender,
        pr.first_name, pr.last_name, pr.oc, pr.contract_status, pr.contract_type,
        pr.gender_identity, pr.sex, pr.pronouns, pr.current_position,
        pr.country_of_work, pr.project_of_work, pr.personal_email, pr.msf_email,
        pr.hrco_email, pr.career_manager_email, pr.line_manager_email, pr.phone_number,
        pr.dietary_requirements, pr.accommodation_needs, pr.certificate_name,
        pr.code_of_conduct_confirm, pr.travel_requirements_confirm
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
    
    result = []
    for p in participants:
        # Data privacy: anonymize personal data for not_selected participants
        if p.status == "not_selected":
            result.append({
                "id": p.id,
                "email": "[REDACTED]",
                "full_name": p.full_name,  # Keep name for audit purposes
                "role": p.role,
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
                "code_of_conduct_confirm": "[REDACTED]",
                "travel_requirements_confirm": "[REDACTED]"
            })
        else:
            result.append({
                "id": p.id,
                "email": p.email,
                "full_name": p.full_name,
                "role": p.role,
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
                "code_of_conduct_confirm": p.code_of_conduct_confirm,
                "travel_requirements_confirm": p.travel_requirements_confirm
            })
    
    return result

@router.get("/participant/{participant_id}")
async def get_participant_details(
    participant_id: int,
    db: Session = Depends(get_db)
):
    """Get detailed information for a specific participant"""
    
    try:
        participant = db.query(EventParticipant).filter(
            EventParticipant.id == participant_id
        ).first()
        
        if not participant:
            raise HTTPException(status_code=404, detail="Participant not found")
        
        # Get user details if available
        user = None
        try:
            user = db.query(User).filter(User.email == participant.email).first()
        except Exception as e:
            print(f"Error fetching user details for {participant.email}: {e}")
        
        return {
            "id": participant.id,
            "email": participant.email,
            "full_name": participant.full_name,
            "phone": user.phone_number if user and hasattr(user, 'phone_number') else None,
            "role": participant.role,
            "status": participant.status,
            "registration_type": "self",
            "registered_by": participant.invited_by,
            "created_at": participant.created_at.isoformat() if participant.created_at else None,
            "updated_at": participant.updated_at.isoformat() if participant.updated_at else None,
            "invitation_sent": participant.status == "selected" and participant.email and participant.email.strip(),
            "invitation_sent_at": participant.updated_at.isoformat() if participant.status == "selected" and participant.email and participant.email.strip() and participant.updated_at else None,
            "invitation_accepted": participant.status == "confirmed",
            "invitation_accepted_at": participant.updated_at.isoformat() if participant.status == "confirmed" and participant.updated_at else None,
            # Registration details
            "country": participant.country,
            "position": participant.position,
            "department": participant.project,  # project field stores department
            "gender": participant.gender,
            "eta": participant.eta,
            "requires_eta": participant.requires_eta,
            "passport_document": bool(participant.passport_document),
            "ticket_document": bool(participant.ticket_document)
        }
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error in get_participant_details: {e}")
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
        # Check if there are existing voucher allocations for this event
        existing_voucher_allocations = db.query(EventAllocation).filter(
            EventAllocation.event_id == participant.event_id,
            EventAllocation.drink_vouchers_per_participant > 0
        ).all()
        
        if existing_voucher_allocations:
            print(f"✅ VOUCHERS ALREADY ALLOCATED for event {participant.event_id}")
            return True
        
        # Get event details for tenant_id
        event = db.query(Event).filter(Event.id == participant.event_id).first()
        if not event:
            print(f"❌ EVENT NOT FOUND for participant {participant.id}")
            return False
        
        # Create automatic voucher allocation (2 vouchers per participant)
        voucher_allocation = EventAllocation(
            event_id=participant.event_id,
            inventory_item_id=1,  # Dummy inventory item
            quantity_per_participant=0,
            drink_vouchers_per_participant=2,  # Default 2 vouchers per participant
            notes="AUTO_ALLOCATED|NOTES:Automatically allocated to selected participants",
            status="approved",  # Auto-approve
            tenant_id=event.tenant_id,
            created_by="system",
            approved_by="system",
            approved_at=datetime.utcnow()
        )
        
        db.add(voucher_allocation)
        db.commit()
        db.refresh(voucher_allocation)
        
        print(f"✅ AUTO-ALLOCATED 2 DRINK VOUCHERS for event {participant.event_id} (allocation ID: {voucher_allocation.id})")
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
    
    participant = db.query(EventParticipant).filter(
        EventParticipant.id == participant_id
    ).first()
    
    if not participant:
        raise HTTPException(status_code=404, detail="Participant not found")
    
    try:
        # Delete related public registration data if exists
        from sqlalchemy import text
        db.execute(text("DELETE FROM public_registrations WHERE participant_id = :participant_id"), 
                  {"participant_id": participant_id})
        
        # Delete the participant
        db.delete(participant)
        db.commit()
        
        return {"message": "Participant deleted successfully"}
        
    except Exception as e:
        db.rollback()
        print(f"Error deleting participant: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete participant")

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