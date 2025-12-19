from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.models.event import Event
from app.models.event_participant import EventParticipant
from pydantic import BaseModel
from typing import Optional, List
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

class PublicRegistrationRequest(BaseModel):
    eventId: int
    # Core required fields
    firstName: str
    lastName: str
    oc: str
    contractStatus: str
    contractType: str
    genderIdentity: str
    sex: str
    pronouns: str
    currentPosition: str
    personalEmail: str
    phoneNumber: str
    travellingInternationally: str
    accommodationType: str
    codeOfConductConfirm: str
    travelRequirementsConfirm: str
    
    # Optional fields
    countryOfWork: Optional[str] = ""
    projectOfWork: Optional[str] = ""
    msfEmail: Optional[str] = ""
    hrcoEmail: Optional[str] = ""
    careerManagerEmail: Optional[str] = ""
    lineManagerEmail: Optional[str] = ""
    travellingFromCountry: Optional[str] = ""
    dietaryRequirements: Optional[str] = ""
    accommodationNeeds: Optional[str] = ""
    dailyMeals: Optional[list] = []
    certificateName: Optional[str] = ""
    badgeName: Optional[str] = ""
    motivationLetter: Optional[str] = ""
    
    # Dynamic form fields (any additional fields)
    class Config:
        extra = "allow"  # Allow additional fields for dynamic form data

@router.post("/check-email-registration")
async def check_email_registration(
    request: dict,
    db: Session = Depends(get_db)
):
    """Check if email is already registered for an event"""
    
    event_id = request.get("event_id")
    personal_email = request.get("personal_email", "").strip().lower()
    msf_email = request.get("msf_email", "").strip().lower()
    
    if not event_id or (not personal_email and not msf_email):
        raise HTTPException(status_code=400, detail="Event ID and at least one email required")
    
    # Check if any of the emails are already registered
    from sqlalchemy import text, or_
    
    existing = db.execute(
        text("""
            SELECT pr.personal_email, pr.msf_email, pr.first_name, pr.last_name
            FROM public_registrations pr
            WHERE pr.event_id = :event_id 
            AND (LOWER(pr.personal_email) = :personal_email OR LOWER(pr.msf_email) = :msf_email)
            LIMIT 1
        """),
        {
            "event_id": event_id,
            "personal_email": personal_email,
            "msf_email": msf_email
        }
    ).fetchone()
    
    if existing:
        return {
            "already_registered": True,
            "message": f"Email already registered for this event by {existing[2]} {existing[3]}",
            "registered_email": existing[0] if existing[0].lower() in [personal_email, msf_email] else existing[1]
        }
    
    return {"already_registered": False}

@router.get("/test-debug")
async def test_debug():
    """Test endpoint to verify debug changes are deployed"""
    print("🔥 BASIC DEBUG: Test endpoint called - changes are deployed!")
    return {"message": "Debug test successful", "timestamp": "2024-10-13"}

@router.get("/events/{event_id}/public")
async def get_public_event(
    event_id: int,
    db: Session = Depends(get_db)
):
    """Get public event details for registration form"""
    
    from sqlalchemy import text
    
    # Get event with tenant information
    result = db.execute(
        text("""
            SELECT e.id, e.title, e.description, e.start_date, e.end_date, e.location,
                   e.registration_form_title, e.registration_form_description, e.registration_deadline,
                   t.slug as tenant_slug, t.name as tenant_name
            FROM events e
            LEFT JOIN tenants t ON e.tenant_id = t.id
            WHERE e.id = :event_id
        """),
        {"event_id": event_id}
    ).fetchone()
    
    if not result:
        raise HTTPException(status_code=404, detail="Event not found")
    
    return {
        "id": result[0],
        "title": result[1],
        "description": result[2],
        "start_date": result[3],
        "end_date": result[4],
        "location": result[5],
        "registration_form_title": result[6],
        "registration_form_description": result[7],
        "registration_deadline": result[8],
        "tenant_slug": result[9],
        "tenant_name": result[10]
    }

@router.post("/events/{event_id}/public-register")
async def public_register_for_event(
    event_id: int,
    registration: PublicRegistrationRequest,
    db: Session = Depends(get_db)
):
    """Allow public registration for events without authentication"""
    
    logger.info(f"🌐 Public registration request for event {event_id}")
    logger.info(f"   Name: {registration.firstName} {registration.lastName}")
    logger.info(f"   Email: {registration.personalEmail}")
    
    # Check if event exists first
    event = db.query(Event).filter(Event.id == event_id).first()
    
    if not event:
        logger.error(f"❌ Event {event_id} not found")
        raise HTTPException(status_code=404, detail="Event not found")
    
    logger.info(f"📊 Event found - Status: '{event.status}' (type: {type(event.status)})")
    logger.info(f"✅ Event registration allowed regardless of status")
    
    # Determine primary email (MSF email if exists, otherwise personal/tembo email)
    primary_email = registration.msfEmail if registration.msfEmail else registration.personalEmail
    
    # Check if user already registered with any email
    existing = db.query(EventParticipant).filter(
        EventParticipant.event_id == event_id
    ).filter(
        (EventParticipant.email == registration.personalEmail) |
        (EventParticipant.email == registration.msfEmail if registration.msfEmail else False)
    ).first()
    
    if existing:
        logger.error(f"❌ User already registered for event {event_id} with email {existing.email}")
        raise HTTPException(status_code=400, detail="Already registered for this event")
    
    try:
        print(f"🔥 BASIC DEBUG: Starting registration process for {registration.firstName} {registration.lastName}")
        
        # Create participant record using primary email
        participant = EventParticipant(
            event_id=event_id,
            email=primary_email,
            full_name=f"{registration.firstName} {registration.lastName}",
            role="attendee",
            status="registered",
            invited_by="public_form",
            # Store additional registration data
            country=registration.countryOfWork or None,
            travelling_from_country=registration.travellingFromCountry if registration.travellingFromCountry else None,
            position=registration.currentPosition,
            project=registration.projectOfWork or None,
            gender=registration.genderIdentity.lower() if registration.genderIdentity in ['Man', 'Woman'] else 'other',
            # Store the missing fields directly in the participant record
            dietary_requirements=registration.dietaryRequirements if registration.dietaryRequirements else None,
            accommodation_type=registration.accommodationType if registration.accommodationType else None
        )
        
        db.add(participant)
        db.commit()
        db.refresh(participant)
        
        # Store detailed registration data in public_registrations table
        from sqlalchemy import text
        
        # Get registration ID for form responses
        registration_result = db.execute(text("""
            INSERT INTO public_registrations (
                event_id, participant_id, first_name, last_name, oc, contract_status, 
                contract_type, gender_identity, sex, pronouns, current_position, 
                country_of_work, project_of_work, personal_email, msf_email, 
                hrco_email, career_manager_email, ld_manager_email, line_manager_email, 
                phone_number, travelling_internationally, travelling_from_country, accommodation_type, 
                dietary_requirements, accommodation_needs, daily_meals, certificate_name,
                badge_name, motivation_letter, code_of_conduct_confirm, travel_requirements_confirm, created_at
            ) VALUES (
                :event_id, :participant_id, :first_name, :last_name, :oc, :contract_status,
                :contract_type, :gender_identity, :sex, :pronouns, :current_position,
                :country_of_work, :project_of_work, :personal_email, :msf_email,
                :hrco_email, :career_manager_email, :ld_manager_email, :line_manager_email,
                :phone_number, :travelling_internationally, :travelling_from_country, :accommodation_type,
                :dietary_requirements, :accommodation_needs, :daily_meals, :certificate_name,
                :badge_name, :motivation_letter, :code_of_conduct_confirm, :travel_requirements_confirm, CURRENT_TIMESTAMP
            ) RETURNING id
        """), {
            "event_id": event_id,
            "participant_id": participant.id,
            "first_name": registration.firstName,
            "last_name": registration.lastName,
            "oc": registration.oc,
            "contract_status": registration.contractStatus,
            "contract_type": registration.contractType,
            "gender_identity": registration.genderIdentity,
            "sex": registration.sex,
            "pronouns": registration.pronouns,
            "current_position": registration.currentPosition,
            "country_of_work": registration.countryOfWork,
            "project_of_work": registration.projectOfWork,
            "personal_email": registration.personalEmail,
            "msf_email": registration.msfEmail,
            "hrco_email": registration.hrcoEmail,
            "career_manager_email": registration.careerManagerEmail,
            "ld_manager_email": registration.lineManagerEmail,
            "line_manager_email": registration.lineManagerEmail,
            "phone_number": registration.phoneNumber,
            "travelling_internationally": registration.travellingInternationally,
            "travelling_from_country": registration.travellingFromCountry,
            "accommodation_type": registration.accommodationType,
            "dietary_requirements": registration.dietaryRequirements,
            "accommodation_needs": registration.accommodationNeeds,
            "daily_meals": ','.join(registration.dailyMeals) if registration.dailyMeals else None,
            "certificate_name": registration.certificateName,
            "badge_name": registration.badgeName,
            "motivation_letter": registration.motivationLetter,
            "code_of_conduct_confirm": registration.codeOfConductConfirm,
            "travel_requirements_confirm": registration.travelRequirementsConfirm
        })
        
        registration_id = registration_result.fetchone()[0]
        
        # Save any additional dynamic form responses
        # This would be handled by the frontend calling the form-responses endpoint separately
        
        # Send line manager recommendation email if line manager email provided
        if registration.lineManagerEmail and registration.lineManagerEmail.strip():
            await send_line_manager_recommendation_email(
                db, event_id, participant.id, registration, event
            )
        
        db.commit()
        
        logger.info(f"✅ Public registration successful for {registration.firstName} {registration.lastName}")
        
        return {
            "message": "Registration successful",
            "participant_id": participant.id,
            "status": "registered"
        }
        
    except Exception as e:
        logger.error(f"❌ Error in public registration: {str(e)}")
        db.rollback()
        raise HTTPException(status_code=400, detail=f"Registration failed: {str(e)}")

async def send_line_manager_recommendation_email(
    db: Session, event_id: int, participant_id: int, registration: PublicRegistrationRequest, event: Event
):
    """Send recommendation request email to line manager"""
    
    import uuid
    from sqlalchemy import text
    
    try:
        # Generate unique token for recommendation
        recommendation_token = str(uuid.uuid4())
        
        # Get registration ID
        registration_result = db.execute(
            text("SELECT id FROM public_registrations WHERE participant_id = :participant_id"),
            {"participant_id": participant_id}
        ).fetchone()
        
        if not registration_result:
            logger.error("Could not find registration record")
            return
        
        registration_id = registration_result[0]
        
        # Insert recommendation record
        db.execute(
            text("""
                INSERT INTO line_manager_recommendations (
                    registration_id, event_id, participant_name, participant_email,
                    line_manager_email, operation_center, event_title, event_dates,
                    event_location, recommendation_token
                ) VALUES (
                    :registration_id, :event_id, :participant_name, :participant_email,
                    :line_manager_email, :operation_center, :event_title, :event_dates,
                    :event_location, :recommendation_token
                )
            """),
            {
                "registration_id": registration_id,
                "event_id": event_id,
                "participant_name": f"{registration.firstName} {registration.lastName}",
                "participant_email": registration.personalEmail,
                "line_manager_email": registration.lineManagerEmail,
                "operation_center": registration.oc,
                "event_title": event.title,
                "event_dates": f"{event.start_date} to {event.end_date}",
                "event_location": event.location,
                "recommendation_token": recommendation_token
            }
        )
        
        db.commit()
        
        # Send email to line manager
        from app.core.email_service import email_service
        import os

        # Get base URL from environment variable, fallback to production URL
        base_url = os.getenv("FRONTEND_BASE_URL", "http://41.90.97.253:8001/portal")
        recommendation_url = f"{base_url}/public/line-manager-recommendation/{recommendation_token}"
        
        subject = f"Recommendation Request - {registration.firstName} {registration.lastName} for {event.title}"
        
        message = f"""
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <h2 style="color: #dc2626;">Line Manager Recommendation Request</h2>
            
            <p>Dear Line Manager,</p>
            
            <p><strong>{registration.firstName} {registration.lastName}</strong> has registered for the following event and listed you as their line manager:</p>
            
            <div style="background-color: #f9fafb; padding: 20px; border-radius: 8px; margin: 20px 0;">
                <h3 style="margin-top: 0; color: #374151;">Event Details</h3>
                <p><strong>Event:</strong> {event.title}</p>
                <p><strong>Dates:</strong> {event.start_date} to {event.end_date}</p>
                <p><strong>Location:</strong> {event.location}</p>
                <p><strong>Operation Center:</strong> {registration.oc}</p>
            </div>
            
            <div style="background-color: #fef3c7; padding: 20px; border-radius: 8px; margin: 20px 0;">
                <h3 style="margin-top: 0; color: #92400e;">Participant Information</h3>
                <p><strong>Name:</strong> {registration.firstName} {registration.lastName}</p>
                <p><strong>Email:</strong> {registration.personalEmail}</p>
                <p><strong>Position:</strong> {registration.currentPosition}</p>
                <p><strong>Country of Work:</strong> {registration.countryOfWork or 'Not specified'}</p>
            </div>
            
            <p>Please click the link below to provide your recommendation:</p>
            
            <div style="text-align: center; margin: 30px 0;">
                <a href="{recommendation_url}" 
                   style="background-color: #dc2626; color: white; padding: 12px 24px; text-decoration: none; border-radius: 6px; font-weight: bold;">
                   Provide Recommendation
                </a>
            </div>
            
            <p style="color: #6b7280; font-size: 14px;">
                This link is unique to this request and will expire after the event registration deadline.
                If you have any questions, please contact the event organizers.
            </p>
        </div>
        """
        
        email_service.send_notification_email(
            to_email=registration.lineManagerEmail,
            user_name="Line Manager",
            title=subject,
            message=message
        )
        
        logger.info(f"✅ Recommendation email sent to {registration.lineManagerEmail}")
        
    except Exception as e:
        logger.error(f"❌ Error sending recommendation email: {e}")
        # Don't fail the registration if email fails
        pass

# ==================== Dynamic Form Field Endpoints ====================

from app.models.form_field import FormField, FormResponse
from datetime import datetime
import json

class PublicFormFieldResponse(BaseModel):
    id: int
    field_name: str
    field_label: str
    field_type: str
    field_options: Optional[List[str]] = None
    is_required: bool
    order_index: int
    section: Optional[str] = None

class ParticipantStatusResponse(BaseModel):
    status: Optional[str] = None
    show_travel_section: bool
    participant_found: bool

@router.get("/events/{event_id}/form-fields")
async def get_public_form_fields(
    event_id: int,
    db: Session = Depends(get_db)
):
    """
    Get all active form fields for public registration form.
    Returns dynamic form fields configured by admin.
    """
    event = db.query(Event).filter(Event.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    fields = db.query(FormField).filter(
        FormField.event_id == event_id,
        FormField.is_active == True
    ).order_by(FormField.order_index).all()

    result = []
    for field in fields:
        field_data = {
            "id": field.id,
            "field_name": field.field_name,
            "field_label": field.field_label,
            "field_type": field.field_type,
            "is_required": field.is_required,
            "order_index": field.order_index,
            "section": field.section if hasattr(field, 'section') else None,
            "field_options": json.loads(field.field_options) if field.field_options else None
        }
        result.append(field_data)

    return result

@router.get("/events/{event_id}/participant-status")
async def check_participant_status(
    event_id: int,
    email: str,
    db: Session = Depends(get_db)
):
    """
    Check if participant is selected for the event.
    Determines if Travel & Accommodation section should be shown.
    """
    participant = db.query(EventParticipant).filter(
        EventParticipant.event_id == event_id,
        EventParticipant.email == email
    ).first()

    if not participant:
        return {
            "status": None,
            "show_travel_section": False,
            "participant_found": False
        }

    # Only show travel section if participant is SELECTED
    show_travel = participant.status and participant.status.lower() == "selected"

    return {
        "status": participant.status,
        "show_travel_section": show_travel,
        "participant_found": True
    }

@router.get("/events/{event_id}/can-register")
async def check_registration_status(
    event_id: int,
    db: Session = Depends(get_db)
):
    """
    Check if event is accepting registrations.
    Validates event dates and registration deadline.
    """
    event = db.query(Event).filter(Event.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    now = datetime.utcnow()
    can_register = True
    reason = None

    # Check if event has started
    if event.start_date and datetime.fromisoformat(str(event.start_date)) <= now:
        can_register = False
        reason = "Event has already started"

    # Check if event has ended
    elif event.end_date and datetime.fromisoformat(str(event.end_date)) <= now:
        can_register = False
        reason = "Event has ended"

    # Check if registration deadline has passed
    elif event.registration_deadline and datetime.fromisoformat(str(event.registration_deadline)) <= now:
        can_register = False
        reason = "Registration deadline has passed"

    return {
        "can_register": can_register,
        "reason": reason,
        "event_title": event.title,
        "start_date": str(event.start_date),
        "end_date": str(event.end_date),
        "registration_deadline": str(event.registration_deadline) if event.registration_deadline else None
    }

@router.post("/events/{event_id}/form-responses")
async def save_form_responses(
    event_id: int,
    responses: dict,
    db: Session = Depends(get_db)
):
    """
    Save dynamic form field responses for a registration.
    """
    try:
        registration_id = responses.get("registration_id")
        form_responses = responses.get("responses", {})
        
        if not registration_id:
            raise HTTPException(status_code=400, detail="Registration ID required")
        
        # Save each form response
        for field_id, value in form_responses.items():
            if value:  # Only save non-empty responses
                form_response = FormResponse(
                    registration_id=registration_id,
                    field_id=int(field_id),
                    field_value=str(value)
                )
                db.add(form_response)
        
        db.commit()
        return {"message": "Form responses saved successfully"}
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to save responses: {str(e)}")
