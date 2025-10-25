from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api import deps
from app.crud.country_travel_requirements import country_travel_requirement
from app.schemas.country_travel_requirements import (
    CountryTravelRequirement,
    CountryTravelRequirementCreate,
    CountryTravelRequirementUpdate
)
from app.models.user import User

router = APIRouter()

@router.get("/tenant/{tenant_id}", response_model=List[CountryTravelRequirement])
def get_tenant_travel_requirements(
    tenant_id: int,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user)
):
    """Get all travel requirements for a tenant"""
    requirements = country_travel_requirement.get_by_tenant(db, tenant_id=tenant_id)
    return requirements

@router.get("/tenant/{tenant_id}/country/{country}", response_model=CountryTravelRequirement)
def get_country_travel_requirement(
    tenant_id: int,
    country: str,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user)
):
    """Get travel requirements for a specific country and tenant"""
    requirement = country_travel_requirement.get_by_tenant_and_country(
        db, tenant_id=tenant_id, country=country
    )
    if not requirement:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Travel requirements not found for this country"
        )
    return requirement

@router.post("/tenant/{tenant_id}", response_model=CountryTravelRequirement)
def create_travel_requirement(
    tenant_id: int,
    requirement_in: CountryTravelRequirementCreate,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user)
):
    """Create travel requirements for a country"""
    # Check if requirement already exists
    existing = country_travel_requirement.get_by_tenant_and_country(
        db, tenant_id=tenant_id, country=requirement_in.country
    )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Travel requirements already exist for this country"
        )
    
    requirement = country_travel_requirement.create_with_tenant(
        db, obj_in=requirement_in, tenant_id=tenant_id, created_by=current_user.email
    )
    return requirement

@router.put("/tenant/{tenant_id}/country/{country}", response_model=CountryTravelRequirement)
def update_travel_requirement(
    tenant_id: int,
    country: str,
    requirement_in: CountryTravelRequirementUpdate,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user)
):
    """Update travel requirements for a country"""
    requirement = country_travel_requirement.get_by_tenant_and_country(
        db, tenant_id=tenant_id, country=country
    )
    if not requirement:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Travel requirements not found for this country"
        )
    
    requirement = country_travel_requirement.update_with_user(
        db, db_obj=requirement, obj_in=requirement_in, updated_by=current_user.email
    )
    return requirement

@router.delete("/tenant/{tenant_id}/country/{country}")
def delete_travel_requirement(
    tenant_id: int,
    country: str,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user)
):
    """Delete travel requirements for a country"""
    requirement = country_travel_requirement.get_by_tenant_and_country(
        db, tenant_id=tenant_id, country=country
    )
    if not requirement:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Travel requirements not found for this country"
        )
    
    country_travel_requirement.remove(db, id=requirement.id)
    return {"message": "Travel requirements deleted successfully"}