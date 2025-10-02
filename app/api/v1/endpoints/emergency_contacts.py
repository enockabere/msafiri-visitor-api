from typing import Any, List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app import crud, schemas
from app.api import deps
from app.db.database import get_db

router = APIRouter()

@router.get("/", response_model=List[schemas.EmergencyContact])
def get_emergency_contacts(
    db: Session = Depends(get_db),
    current_user: schemas.User = Depends(deps.get_current_user)
) -> Any:
    """Get all emergency contacts for current user"""
    contacts = crud.emergency_contact.get_by_user(db, user_id=current_user.id)
    return contacts

@router.post("/", response_model=schemas.EmergencyContact)
def create_emergency_contact(
    *,
    db: Session = Depends(get_db),
    contact_in: schemas.EmergencyContactCreate,
    current_user: schemas.User = Depends(deps.get_current_user)
) -> Any:
    """Create new emergency contact"""
    contact = crud.emergency_contact.create_with_user(
        db, obj_in=contact_in, user_id=current_user.id
    )
    return contact

@router.put("/{contact_id}", response_model=schemas.EmergencyContact)
def update_emergency_contact(
    *,
    db: Session = Depends(get_db),
    contact_id: int,
    contact_in: schemas.EmergencyContactUpdate,
    current_user: schemas.User = Depends(deps.get_current_user)
) -> Any:
    """Update emergency contact"""
    contact = crud.emergency_contact.get(db, id=contact_id)
    if not contact:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Emergency contact not found"
        )
    
    try:
        contact = crud.emergency_contact.update_with_user_check(
            db, db_obj=contact, obj_in=contact_in, user_id=current_user.id
        )
        return contact
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )

@router.delete("/{contact_id}")
def delete_emergency_contact(
    *,
    db: Session = Depends(get_db),
    contact_id: int,
    current_user: schemas.User = Depends(deps.get_current_user)
) -> Any:
    """Delete emergency contact"""
    contact = crud.emergency_contact.get(db, id=contact_id)
    if not contact:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Emergency contact not found"
        )
    
    if contact.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Emergency contact does not belong to user"
        )
    
    crud.emergency_contact.remove(db, id=contact_id)
    return {"message": "Emergency contact deleted successfully"}