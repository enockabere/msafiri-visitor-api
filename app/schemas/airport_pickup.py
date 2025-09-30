from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

class AirportPickupBase(BaseModel):
    driver_name: str
    driver_phone: str
    driver_email: Optional[str] = None
    vehicle_details: Optional[str] = None
    pickup_time: datetime
    destination: str
    special_instructions: Optional[str] = None
    travel_agent_email: Optional[str] = None

class AirportPickupCreate(AirportPickupBase):
    participant_id: int

class AirportPickupUpdate(BaseModel):
    driver_name: Optional[str] = None
    driver_phone: Optional[str] = None
    pickup_time: Optional[datetime] = None
    destination: Optional[str] = None
    special_instructions: Optional[str] = None

class AirportPickup(AirportPickupBase):
    id: int
    participant_id: int
    driver_confirmed: bool
    visitor_confirmed: bool
    admin_confirmed: bool
    welcome_package_confirmed: bool
    pickup_completed: bool
    created_by: str
    created_at: datetime
    
    class Config:
        from_attributes = True

class TravelAgentBase(BaseModel):
    email: str
    name: str
    company_name: str
    phone: str

class TravelAgentCreate(TravelAgentBase):
    pass

class TravelAgent(TravelAgentBase):
    id: int
    is_active: bool
    tenant_id: str
    api_token: str
    created_at: datetime
    
    class Config:
        from_attributes = True

class PickupConfirmation(BaseModel):
    confirmation_type: str  # "driver", "visitor", "admin", "welcome_package"
    notes: Optional[str] = None

class TravelAgentPickupView(BaseModel):
    pickup_id: int
    participant_name: str
    participant_email: str
    participant_phone: Optional[str] = None
    flight_number: Optional[str] = None
    arrival_time: Optional[datetime] = None
    pickup_time: datetime
    destination: str
    driver_name: str
    driver_phone: str
    vehicle_details: Optional[str] = None
    special_instructions: Optional[str] = None
    welcome_packages: List[dict]
    confirmations_status: dict