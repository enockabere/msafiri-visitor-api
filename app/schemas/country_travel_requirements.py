from pydantic import BaseModel
from typing import Optional

class CountryTravelRequirementBase(BaseModel):
    country: str
    visa_required: bool = False
    eta_required: bool = False
    passport_required: bool = True
    flight_ticket_required: bool = True

class CountryTravelRequirementCreate(CountryTravelRequirementBase):
    pass

class CountryTravelRequirementUpdate(BaseModel):
    visa_required: Optional[bool] = None
    eta_required: Optional[bool] = None
    passport_required: Optional[bool] = None
    flight_ticket_required: Optional[bool] = None

class CountryTravelRequirement(CountryTravelRequirementBase):
    id: int
    tenant_id: int
    created_by: str
    updated_by: Optional[str] = None
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True