from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.orm import Session
from sqlalchemy import and_
from typing import List, Optional
from datetime import datetime
import secrets
from app.db.database import get_db
from app.models.airport_pickup import AirportPickup
from app.models.travel_agent import TravelAgent
from app.models.event_participant import EventParticipant
from app.models.travel_ticket import ParticipantTicket
from app.models.welcome_package import EventWelcomePackage
from app.schemas.airport_pickup import (
    AirportPickupCreate, AirportPickupUpdate, AirportPickup as PickupSchema,
    TravelAgentCreate, TravelAgent as AgentSchema, PickupConfirmation,
    TravelAgentPickupView
)
from app.api.deps import get_current_user
from app.models.user import User

router = APIRouter()

# Admin endpoints for pickup management
@router.post("/", response_model=PickupSchema)
def create_airport_pickup(
    pickup: AirportPickupCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Admin creates airport pickup arrangement"""
    if current_user.role not in ["MT_ADMIN", "HR_ADMIN", "EVENT_ADMIN"]:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    # Check if pickup already exists
    existing = db.query(AirportPickup).filter(
        AirportPickup.participant_id == pickup.participant_id
    ).first()
    
    if existing:
        raise HTTPException(status_code=400, detail="Pickup already arranged for this participant")
    
    db_pickup = AirportPickup(
        **pickup.dict(),
        created_by=current_user.email
    )
    db.add(db_pickup)
    db.commit()
    db.refresh(db_pickup)
    return db_pickup

@router.get("/", response_model=List[dict])
def get_all_pickups(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Admin gets all pickup arrangements"""
    if current_user.role not in ["MT_ADMIN", "HR_ADMIN", "EVENT_ADMIN"]:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    pickups = db.query(AirportPickup, EventParticipant, ParticipantTicket).join(
        EventParticipant, AirportPickup.participant_id == EventParticipant.id
    ).outerjoin(
        ParticipantTicket, ParticipantTicket.participant_id == EventParticipant.id
    ).all()
    
    result = []
    for pickup, participant, ticket in pickups:
        result.append({
            "pickup_id": pickup.id,
            "participant_name": participant.full_name or participant.email,
            "participant_email": participant.email,
            "flight_info": {
                "flight_number": ticket.flight_number if ticket else None,
                "arrival_date": str(ticket.arrival_date) if ticket else None,
                "arrival_airport": ticket.arrival_airport if ticket else None
            },
            "pickup_details": {
                "driver_name": pickup.driver_name,
                "pickup_time": pickup.pickup_time,
                "destination": pickup.destination,
                "vehicle_details": pickup.vehicle_details
            },
            "confirmations": {
                "driver_confirmed": pickup.driver_confirmed,
                "visitor_confirmed": pickup.visitor_confirmed,
                "admin_confirmed": pickup.admin_confirmed,
                "welcome_package_confirmed": pickup.welcome_package_confirmed,
                "pickup_completed": pickup.pickup_completed
            }
        })
    
    return result

@router.put("/{pickup_id}", response_model=PickupSchema)
def update_pickup(
    pickup_id: int,
    pickup_update: AirportPickupUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Admin updates pickup details"""
    if current_user.role not in ["MT_ADMIN", "HR_ADMIN", "EVENT_ADMIN"]:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    pickup = db.query(AirportPickup).filter(AirportPickup.id == pickup_id).first()
    if not pickup:
        raise HTTPException(status_code=404, detail="Pickup not found")
    
    for field, value in pickup_update.dict(exclude_unset=True).items():
        setattr(pickup, field, value)
    
    db.commit()
    db.refresh(pickup)
    return pickup

# Travel agent management
@router.post("/travel-agents/", response_model=AgentSchema)
def create_travel_agent(
    agent: TravelAgentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Admin creates travel agent with API access"""
    if current_user.role not in ["MT_ADMIN", "HR_ADMIN", "EVENT_ADMIN"]:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    # Generate API token
    api_token = secrets.token_urlsafe(32)
    
    db_agent = TravelAgent(
        **agent.dict(),
        tenant_id=current_user.tenant_id,
        created_by=current_user.email,
        api_token=api_token
    )
    db.add(db_agent)
    db.commit()
    db.refresh(db_agent)
    return db_agent

@router.get("/travel-agents/", response_model=List[AgentSchema])
def get_travel_agents(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Admin gets all travel agents"""
    if current_user.role not in ["MT_ADMIN", "HR_ADMIN", "EVENT_ADMIN"]:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    return db.query(TravelAgent).filter(TravelAgent.tenant_id == current_user.tenant_id).all()

# Travel agent endpoints (limited access)
@router.get("/agent/my-pickups", response_model=List[TravelAgentPickupView])
def get_agent_pickups(
    agent_token: str = Header(..., alias="X-Agent-Token"),
    db: Session = Depends(get_db)
):
    """Travel agent gets assigned pickups"""
    
    # Verify agent token
    agent = db.query(TravelAgent).filter(
        and_(
            TravelAgent.api_token == agent_token,
            TravelAgent.is_active == True
        )
    ).first()
    
    if not agent:
        raise HTTPException(status_code=401, detail="Invalid agent token")
    
    # Get pickups assigned to this agent
    pickups = db.query(AirportPickup, EventParticipant, ParticipantTicket).join(
        EventParticipant, AirportPickup.participant_id == EventParticipant.id
    ).outerjoin(
        ParticipantTicket, ParticipantTicket.participant_id == EventParticipant.id
    ).filter(AirportPickup.travel_agent_email == agent.email).all()
    
    result = []
    for pickup, participant, ticket in pickups:
        # Get welcome packages
        welcome_packages = db.query(EventWelcomePackage).filter(
            EventWelcomePackage.event_id == participant.event_id
        ).all()
        
        packages_data = [
            {
                "item_name": pkg.item_name,
                "description": pkg.description,
                "quantity": pkg.quantity_per_participant,
                "is_functional_phone": pkg.is_functional_phone
            }
            for pkg in welcome_packages
        ]
        
        result.append(TravelAgentPickupView(
            pickup_id=pickup.id,
            participant_name=participant.full_name or participant.email,
            participant_email=participant.email,
            participant_phone=getattr(participant, 'phone', None),
            flight_number=ticket.flight_number if ticket else None,
            arrival_time=ticket.arrival_date if ticket else None,
            pickup_time=pickup.pickup_time,
            destination=pickup.destination,
            driver_name=pickup.driver_name,
            driver_phone=pickup.driver_phone,
            vehicle_details=pickup.vehicle_details,
            special_instructions=pickup.special_instructions,
            welcome_packages=packages_data,
            confirmations_status={
                "driver_confirmed": pickup.driver_confirmed,
                "visitor_confirmed": pickup.visitor_confirmed,
                "welcome_package_confirmed": pickup.welcome_package_confirmed,
                "pickup_completed": pickup.pickup_completed
            }
        ))
    
    return result

@router.post("/agent/{pickup_id}/confirm")
def agent_confirm_pickup(
    pickup_id: int,
    confirmation: PickupConfirmation,
    agent_token: str = Header(..., alias="X-Agent-Token"),
    db: Session = Depends(get_db)
):
    """Travel agent confirms pickup details"""
    
    # Verify agent
    agent = db.query(TravelAgent).filter(
        and_(
            TravelAgent.api_token == agent_token,
            TravelAgent.is_active == True
        )
    ).first()
    
    if not agent:
        raise HTTPException(status_code=401, detail="Invalid agent token")
    
    pickup = db.query(AirportPickup).filter(
        and_(
            AirportPickup.id == pickup_id,
            AirportPickup.travel_agent_email == agent.email
        )
    ).first()
    
    if not pickup:
        raise HTTPException(status_code=404, detail="Pickup not found or not assigned to you")
    
    # Update confirmation based on type
    if confirmation.confirmation_type == "driver":
        pickup.driver_confirmed = True
        pickup.driver_confirmation_time = datetime.now()
    elif confirmation.confirmation_type == "welcome_package":
        pickup.welcome_package_confirmed = True
    elif confirmation.confirmation_type == "pickup_completed":
        pickup.pickup_completed = True
    
    db.commit()
    return {"message": f"{confirmation.confirmation_type} confirmed"}

# Visitor endpoints
@router.get("/my-pickup")
def get_my_pickup(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Visitor gets their pickup details"""
    
    pickup = db.query(AirportPickup, EventParticipant).join(
        EventParticipant, AirportPickup.participant_id == EventParticipant.id
    ).filter(EventParticipant.email == current_user.email).first()
    
    if not pickup:
        raise HTTPException(status_code=404, detail="No pickup arranged")
    
    pickup_info, participant = pickup
    
    return {
        "driver_name": pickup_info.driver_name,
        "driver_phone": pickup_info.driver_phone,
        "pickup_time": pickup_info.pickup_time,
        "destination": pickup_info.destination,
        "vehicle_details": pickup_info.vehicle_details,
        "special_instructions": pickup_info.special_instructions,
        "visitor_confirmed": pickup_info.visitor_confirmed,
        "pickup_completed": pickup_info.pickup_completed
    }

@router.post("/my-pickup/confirm")
def confirm_my_pickup(
    confirmation: PickupConfirmation,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Visitor confirms pickup or welcome package receipt"""
    
    pickup = db.query(AirportPickup).join(
        EventParticipant, AirportPickup.participant_id == EventParticipant.id
    ).filter(EventParticipant.email == current_user.email).first()
    
    if not pickup:
        raise HTTPException(status_code=404, detail="No pickup found")
    
    if confirmation.confirmation_type == "visitor":
        pickup.visitor_confirmed = True
        pickup.visitor_confirmation_time = datetime.now()
    elif confirmation.confirmation_type == "welcome_package":
        pickup.welcome_package_confirmed = True
    
    db.commit()
    return {"message": "Confirmation recorded"}

# Admin confirmation (for users who can't confirm themselves)
@router.post("/{pickup_id}/admin-confirm")
def admin_confirm_pickup(
    pickup_id: int,
    confirmation: PickupConfirmation,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Admin confirms pickup for users who can't confirm themselves"""
    if current_user.role not in ["MT_ADMIN", "HR_ADMIN", "EVENT_ADMIN"]:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    pickup = db.query(AirportPickup).filter(AirportPickup.id == pickup_id).first()
    if not pickup:
        raise HTTPException(status_code=404, detail="Pickup not found")
    
    pickup.admin_confirmed = True
    pickup.admin_confirmation_time = datetime.now()
    pickup.confirmed_by_admin = current_user.email
    
    if confirmation.confirmation_type == "visitor":
        pickup.visitor_confirmed = True
    elif confirmation.confirmation_type == "welcome_package":
        pickup.welcome_package_confirmed = True
    elif confirmation.confirmation_type == "pickup_completed":
        pickup.pickup_completed = True
    
    db.commit()
    return {"message": "Admin confirmation recorded"}