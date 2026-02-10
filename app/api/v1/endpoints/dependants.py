"""Dependants API endpoints - for managing user's family members."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, date
from pydantic import BaseModel, Field
import logging

from app.db.database import get_db
from app.models.travel_request import Dependant, DependantRelationship
from app.models.user import User
from app.api.deps import get_current_user

router = APIRouter()
logger = logging.getLogger(__name__)


# ===== Schemas =====

class DependantBase(BaseModel):
    """Base schema for dependant."""
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)
    relation_type: DependantRelationship
    date_of_birth: Optional[date] = None
    passport_number: Optional[str] = Field(None, max_length=50)
    passport_expiry: Optional[date] = None
    nationality: Optional[str] = Field(None, max_length=100)
    phone_number: Optional[str] = Field(None, max_length=50)
    email: Optional[str] = Field(None, max_length=255)


class DependantCreate(DependantBase):
    """Schema for creating a dependant."""
    pass


class DependantUpdate(BaseModel):
    """Schema for updating a dependant."""
    first_name: Optional[str] = Field(None, min_length=1, max_length=100)
    last_name: Optional[str] = Field(None, min_length=1, max_length=100)
    relation_type: Optional[DependantRelationship] = None
    date_of_birth: Optional[date] = None
    passport_number: Optional[str] = Field(None, max_length=50)
    passport_expiry: Optional[date] = None
    nationality: Optional[str] = Field(None, max_length=100)
    phone_number: Optional[str] = Field(None, max_length=50)
    email: Optional[str] = Field(None, max_length=255)


class DependantResponse(DependantBase):
    """Schema for dependant response."""
    id: int
    user_id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ===== Endpoints =====

@router.get("/", response_model=List[DependantResponse])
async def get_my_dependants(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get all dependants for the current user."""
    dependants = db.query(Dependant).filter(
        Dependant.user_id == current_user.id
    ).order_by(Dependant.first_name).all()

    return dependants


@router.post("/", response_model=DependantResponse, status_code=status.HTTP_201_CREATED)
async def create_dependant(
    dependant_data: DependantCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new dependant."""
    logger.info(f"Creating dependant for user {current_user.id}: {dependant_data.first_name} {dependant_data.last_name}")
    
    dependant = Dependant(
        user_id=current_user.id,
        first_name=dependant_data.first_name,
        last_name=dependant_data.last_name,
        relation_type=dependant_data.relation_type,
        date_of_birth=dependant_data.date_of_birth,
        passport_number=dependant_data.passport_number,
        passport_expiry=dependant_data.passport_expiry,
        nationality=dependant_data.nationality,
        phone_number=dependant_data.phone_number,
        email=dependant_data.email
    )

    db.add(dependant)
    db.commit()
    db.refresh(dependant)
    
    logger.info(f"Dependant created successfully with ID: {dependant.id}")

    return dependant


@router.get("/{dependant_id}", response_model=DependantResponse)
async def get_dependant(
    dependant_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get a specific dependant."""
    dependant = db.query(Dependant).filter(
        Dependant.id == dependant_id,
        Dependant.user_id == current_user.id
    ).first()

    if not dependant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Dependant not found"
        )

    return dependant


@router.put("/{dependant_id}", response_model=DependantResponse)
async def update_dependant(
    dependant_id: int,
    dependant_data: DependantUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update a dependant."""
    dependant = db.query(Dependant).filter(
        Dependant.id == dependant_id,
        Dependant.user_id == current_user.id
    ).first()

    if not dependant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Dependant not found"
        )

    for field, value in dependant_data.dict(exclude_unset=True).items():
        setattr(dependant, field, value)

    db.commit()
    db.refresh(dependant)

    return dependant


@router.delete("/{dependant_id}")
async def delete_dependant(
    dependant_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete a dependant."""
    dependant = db.query(Dependant).filter(
        Dependant.id == dependant_id,
        Dependant.user_id == current_user.id
    ).first()

    if not dependant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Dependant not found"
        )

    db.delete(dependant)
    db.commit()

    return {"message": "Dependant deleted successfully"}
