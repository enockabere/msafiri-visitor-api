from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import and_
from typing import List
from app.db.database import get_db
from app.models.travel_ticket import ParticipantTicket
from app.models.welcome_package import EventWelcomePackage, ParticipantWelcomeDelivery
from app.models.travel_requirements import EventTravelRequirement, ParticipantRequirementStatus
from app.models.event_participant import EventParticipant
from app.schemas.travel_management import (
    ParticipantTicketCreate, ParticipantTicket as TicketSchema,
    WelcomePackageCreate, WelcomePackage as PackageSchema,
    TravelRequirementCreate, TravelRequirement as RequirementSchema,
    WelcomeDelivery, RequirementCompletion, ParticipantTravelStatus
)
from app.api.deps import get_current_user
from app.models.user import User

router = APIRouter()

# Ticket Management
@router.post("/tickets/", response_model=TicketSchema)
def create_participant_ticket(
    ticket: ParticipantTicketCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create or update participant ticket"""
    if current_user.role not in ["MT_ADMIN", "HR_ADMIN", "EVENT_ADMIN"]:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    # Check if ticket exists
    existing = db.query(ParticipantTicket).filter(
        ParticipantTicket.participant_id == ticket.participant_id
    ).first()
    
    if existing:
        # Update existing ticket
        for field, value in ticket.dict(exclude={'participant_id'}).items():
            setattr(existing, field, value)
        db.commit()
        db.refresh(existing)
        return existing
    else:
        # Create new ticket
        db_ticket = ParticipantTicket(**ticket.dict())
        db.add(db_ticket)
        db.commit()
        db.refresh(db_ticket)
        return db_ticket

@router.get("/tickets/{participant_id}", response_model=TicketSchema)
def get_participant_ticket(participant_id: int, db: Session = Depends(get_db)):
    """Get participant ticket information"""
    ticket = db.query(ParticipantTicket).filter(
        ParticipantTicket.participant_id == participant_id
    ).first()
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    return ticket

# Welcome Package Management
@router.post("/welcome-packages/", response_model=PackageSchema)
def create_welcome_package(
    package: WelcomePackageCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create welcome package item for event"""
    if current_user.role not in ["MT_ADMIN", "HR_ADMIN", "EVENT_ADMIN"]:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    db_package = EventWelcomePackage(
        **package.dict(),
        created_by=current_user.email
    )
    db.add(db_package)
    db.commit()
    db.refresh(db_package)
    return db_package

@router.get("/welcome-packages/{event_id}", response_model=List[PackageSchema])
def get_event_welcome_packages(event_id: int, db: Session = Depends(get_db)):
    """Get welcome packages for event"""
    return db.query(EventWelcomePackage).filter(
        EventWelcomePackage.event_id == event_id
    ).all()

@router.post("/welcome-packages/deliver")
def deliver_welcome_package(
    participant_id: int,
    delivery: WelcomeDelivery,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Mark welcome package as delivered by driver"""
    # Check if delivery record exists
    existing = db.query(ParticipantWelcomeDelivery).filter(
        and_(
            ParticipantWelcomeDelivery.participant_id == participant_id,
            ParticipantWelcomeDelivery.package_item_id == delivery.package_item_id
        )
    ).first()
    
    if existing:
        existing.delivered = delivery.delivered
        existing.delivered_by = current_user.email
        existing.delivery_notes = delivery.delivery_notes
    else:
        new_delivery = ParticipantWelcomeDelivery(
            participant_id=participant_id,
            package_item_id=delivery.package_item_id,
            delivered=delivery.delivered,
            delivered_by=current_user.email,
            delivery_notes=delivery.delivery_notes
        )
        db.add(new_delivery)
    
    db.commit()
    return {"message": "Welcome package delivery updated"}

# Travel Requirements Management
@router.post("/requirements/", response_model=RequirementSchema)
def create_travel_requirement(
    requirement: TravelRequirementCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create travel requirement for event"""
    if current_user.role not in ["MT_ADMIN", "HR_ADMIN", "EVENT_ADMIN"]:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    db_requirement = EventTravelRequirement(
        **requirement.dict(),
        created_by=current_user.email
    )
    db.add(db_requirement)
    db.commit()
    db.refresh(db_requirement)
    return db_requirement

@router.get("/requirements/{event_id}", response_model=List[RequirementSchema])
def get_event_requirements(event_id: int, db: Session = Depends(get_db)):
    """Get travel requirements for event"""
    return db.query(EventTravelRequirement).filter(
        EventTravelRequirement.event_id == event_id
    ).all()

@router.post("/requirements/complete")
def complete_requirement(
    participant_id: int,
    completion: RequirementCompletion,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Mark travel requirement as completed"""
    # Check if status exists
    existing = db.query(ParticipantRequirementStatus).filter(
        and_(
            ParticipantRequirementStatus.participant_id == participant_id,
            ParticipantRequirementStatus.requirement_id == completion.requirement_id
        )
    ).first()
    
    if existing:
        existing.completed = completion.completed
        existing.completion_notes = completion.completion_notes
        existing.completed_by = current_user.email
    else:
        new_status = ParticipantRequirementStatus(
            participant_id=participant_id,
            requirement_id=completion.requirement_id,
            completed=completion.completed,
            completion_notes=completion.completion_notes,
            completed_by=current_user.email
        )
        db.add(new_status)
    
    db.commit()
    return {"message": "Requirement status updated"}

@router.get("/status/{event_id}", response_model=List[ParticipantTravelStatus])
def get_participants_travel_status(
    event_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get travel status for all event participants"""
    if current_user.role not in ["MT_ADMIN", "HR_ADMIN", "EVENT_ADMIN"]:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    participants = db.query(EventParticipant).filter(
        EventParticipant.event_id == event_id
    ).all()
    
    result = []
    for participant in participants:
        # Get ticket
        ticket = db.query(ParticipantTicket).filter(
            ParticipantTicket.participant_id == participant.id
        ).first()
        
        # Get requirements status
        requirements = db.query(EventTravelRequirement).filter(
            EventTravelRequirement.event_id == event_id
        ).all()
        
        req_status = []
        for req in requirements:
            status = db.query(ParticipantRequirementStatus).filter(
                and_(
                    ParticipantRequirementStatus.participant_id == participant.id,
                    ParticipantRequirementStatus.requirement_id == req.id
                )
            ).first()
            
            req_status.append({
                "requirement_id": req.id,
                "title": req.title,
                "type": req.requirement_type.value,
                "completed": status.completed if status else False
            })
        
        # Get welcome packages status
        packages = db.query(EventWelcomePackage).filter(
            EventWelcomePackage.event_id == event_id
        ).all()
        
        package_status = []
        for package in packages:
            delivery = db.query(ParticipantWelcomeDelivery).filter(
                and_(
                    ParticipantWelcomeDelivery.participant_id == participant.id,
                    ParticipantWelcomeDelivery.package_item_id == package.id
                )
            ).first()
            
            package_status.append({
                "package_id": package.id,
                "item_name": package.item_name,
                "delivered": delivery.delivered if delivery else False
            })
        
        result.append(ParticipantTravelStatus(
            participant_id=participant.id,
            participant_name=participant.full_name or "Unknown",
            participant_email=participant.email,
            has_ticket=ticket is not None,
            ticket_info=ticket,
            requirements_status=req_status,
            welcome_packages_status=package_status
        ))
    
    return result
