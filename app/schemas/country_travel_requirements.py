from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime

class AdditionalRequirement(BaseModel):
    name: str
    required: bool = False
    description: Optional[str] = None

class CountryTravelRequirementBase(BaseModel):
    country: str
    visa_required: bool = False
    eta_required: bool = False
    passport_required: bool = True
    flight_ticket_required: bool = True
    additional_requirements: Optional[List[AdditionalRequirement]] = None

class CountryTravelRequirementCreate(CountryTravelRequirementBase):
    pass

class CountryTravelRequirementUpdate(BaseModel):
    visa_required: Optional[bool] = None
    eta_required: Optional[bool] = None
    passport_required: Optional[bool] = None
    flight_ticket_required: Optional[bool] = None
    additional_requirements: Optional[List[AdditionalRequirement]] = None

class CountryTravelRequirement(CountryTravelRequirementBase):
    id: int
    tenant_id: int
    created_by: str
    updated_by: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True
