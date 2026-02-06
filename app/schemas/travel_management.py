from pydantic import BaseModel
from typing import Optional, List
from datetime import date, datetime

# Ticket Schemas
class ParticipantTicketBase(BaseModel):
    departure_date: date
    arrival_date: date
    departure_airport: str
    arrival_airport: str
    flight_number: Optional[str] = None
    airline: Optional[str] = None
    ticket_reference: Optional[str] = None
    notes: Optional[str] = None

class ParticipantTicketCreate(ParticipantTicketBase):
    participant_id: int

class ParticipantTicket(ParticipantTicketBase):
    id: int
    participant_id: int
    created_at: datetime
    
    class Config:
        from_attributes = True

# Welcome Package Schemas
class WelcomePackageBase(BaseModel):
    item_name: str
    description: Optional[str] = None
    quantity_per_participant: int = 1
    is_functional_phone: bool = False
    pickup_instructions: Optional[str] = None

class WelcomePackageCreate(WelcomePackageBase):
    event_id: int

class WelcomePackage(WelcomePackageBase):
    id: int
    event_id: int
    created_by: str
    created_at: datetime
    
    class Config:
        from_attributes = True

class WelcomeDelivery(BaseModel):
    package_item_id: int
    delivered: bool = True
    delivery_notes: Optional[str] = None

# Travel Requirements Schemas
class TravelRequirementBase(BaseModel):
    requirement_type: str  # "eta" or "health"
    title: str
    description: str
    is_mandatory: bool = True
    deadline_days_before: Optional[int] = None

class TravelRequirementCreate(TravelRequirementBase):
    event_id: int

class TravelRequirement(TravelRequirementBase):
    id: int
    event_id: int
    created_by: str
    created_at: datetime
    
    class Config:
        from_attributes = True

class RequirementCompletion(BaseModel):
    requirement_id: int
    completed: bool = True
    completion_notes: Optional[str] = None

class ParticipantTravelStatus(BaseModel):
    participant_id: int
    participant_name: str
    participant_email: str
    has_ticket: bool
    ticket_info: Optional[ParticipantTicket] = None
    requirements_status: List[dict]
    welcome_packages_status: List[dict]
