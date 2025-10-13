from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.models.event import Event
from app.models.event_participant import EventParticipant
from pydantic import BaseModel
from typing import Optional
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

class PublicRegistrationRequest(BaseModel):
    eventId: int
    firstName: str
    lastName: str
    oc: str
    contractStatus: str
    contractType: str
    genderIdentity: str
    sex: str
    pronouns: str
    currentPosition: str
    countryOfWork: Optional[str] = ""
    projectOfWork: Optional[str] = ""
    personalEmail: str
    msfEmail: Optional[str] = ""
    hrcoEmail: Optional[str] = ""
    careerManagerEmail: Optional[str] = ""
    lineManagerEmail: Optional[str] = ""
    phoneNumber: str
    travellingInternationally: Optional[str] = ""
    accommodationType: Optional[str] = ""
    dietaryRequirements: Optional[str] = ""
    accommodationNeeds: Optional[str] = ""
    dailyMeals: Optional[list] = []
    certificateName: Optional[str] = ""
    codeOfConductConfirm: Optional[str] = ""
    travelRequirementsConfirm: Optional[str] = ""

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
            LEFT JOIN tenants t ON e.tenant_id = t.slug
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
            position=registration.currentPosition,
            project=registration.projectOfWork or None,
            gender=registration.genderIdentity.lower() if registration.genderIdentity in ['Man', 'Woman'] else 'other'
        )
        
        db.add(participant)
        db.commit()
        db.refresh(participant)
        
        # Update participant with dietary requirements and accommodation type
        from sqlalchemy import text
        update_participant_sql = """
        UPDATE event_participants 
        SET dietary_requirements = :dietary_requirements,
            accommodation_type = :accommodation_type,
            participant_name = :participant_name,
            participant_email = :participant_email
        WHERE id = :participant_id
        """
        
        db.execute(text(update_participant_sql), {
            "participant_id": participant.id,
            "dietary_requirements": registration.dietaryRequirements if registration.dietaryRequirements else None,
            "accommodation_type": registration.accommodationType if registration.accommodationType else None,
            "participant_name": f"{registration.firstName} {registration.lastName}",
            "participant_email": registration.personalEmail
        })
        
        # Store detailed registration data
        from sqlalchemy import text
        detailed_registration_sql = """
        INSERT INTO public_registrations (
            event_id, participant_id, first_name, last_name, oc, contract_status, 
            contract_type, gender_identity, sex, pronouns, current_position, 
            country_of_work, project_of_work, personal_email, msf_email, 
            hrco_email, career_manager_email, ld_manager_email, line_manager_email, 
            phone_number, dietary_requirements, accommodation_needs, certificate_name,
            code_of_conduct_confirm, travel_requirements_confirm, created_at
        ) VALUES (
            :event_id, :participant_id, :first_name, :last_name, :oc, :contract_status,
            :contract_type, :gender_identity, :sex, :pronouns, :current_position,
            :country_of_work, :project_of_work, :personal_email, :msf_email,
            :hrco_email, :career_manager_email, :ld_manager_email, :line_manager_email,
            :phone_number, :dietary_requirements, :accommodation_needs, :certificate_name,
            :code_of_conduct_confirm, :travel_requirements_confirm, CURRENT_TIMESTAMP
        )
        """
        
        db.execute(text(detailed_registration_sql), {
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
            "dietary_requirements": registration.dietaryRequirements,
            "accommodation_needs": registration.accommodationNeeds,
            "certificate_name": registration.certificateName,
            "code_of_conduct_confirm": registration.codeOfConductConfirm,
            "travel_requirements_confirm": registration.travelRequirementsConfirm
        })
        
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