from fastapi import APIRouter, HTTPException, Depends, Query
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.models.guesthouse import GuestHouse
from pydantic import BaseModel
from typing import Optional, Dict, Any

router = APIRouter()

class GuestHouseCreate(BaseModel):
    name: str
    location: str
    address: str
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    description: Optional[str] = None
    contact_person: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    facilities: Optional[Dict[str, Any]] = None
    house_rules: Optional[str] = None
    check_in_time: Optional[str] = "14:00"
    check_out_time: Optional[str] = "11:00"
    tenant_id: str

@router.get("/")
async def get_guest_houses(
    tenant_context: str = Query(...),
    db: Session = Depends(get_db)
):
    """Get all guest houses for a tenant"""
    try:
        guest_houses = db.query(GuestHouse).filter(
            GuestHouse.tenant_id == tenant_context
        ).all()
        
        result = []
        for gh in guest_houses:
            result.append({
                "id": gh.id,
                "name": gh.name,
                "location": gh.location,
                "address": gh.address,
                "latitude": gh.latitude,
                "longitude": gh.longitude,
                "description": gh.description,
                "contact_person": gh.contact_person,
                "phone": gh.phone,
                "email": gh.email,
                "facilities": gh.facilities or {},
                "house_rules": gh.house_rules,
                "check_in_time": gh.check_in_time,
                "check_out_time": gh.check_out_time,
                "is_active": gh.is_active,
                "tenant_id": gh.tenant_id,
                "created_by": gh.created_by,
                "created_at": gh.created_at.isoformat() if gh.created_at else None,
                "rooms": []  # Empty for now
            })
        
        return result
    except Exception as e:
        print(f"Error fetching guest houses: {e}")
        return []

@router.post("/")
async def create_guest_house(
    guest_house_data: GuestHouseCreate,
    db: Session = Depends(get_db)
):
    """Create a new guest house"""
    try:
        new_guest_house = GuestHouse(
            name=guest_house_data.name,
            location=guest_house_data.location,
            address=guest_house_data.address,
            latitude=guest_house_data.latitude,
            longitude=guest_house_data.longitude,
            description=guest_house_data.description,
            contact_person=guest_house_data.contact_person,
            phone=guest_house_data.phone,
            email=guest_house_data.email,
            facilities=guest_house_data.facilities,
            house_rules=guest_house_data.house_rules,
            check_in_time=guest_house_data.check_in_time,
            check_out_time=guest_house_data.check_out_time,
            tenant_id=guest_house_data.tenant_id,
            created_by="system",
            is_active=True
        )
        
        db.add(new_guest_house)
        db.commit()
        db.refresh(new_guest_house)
        
        return {
            "id": new_guest_house.id,
            "name": new_guest_house.name,
            "message": "Guest house created successfully"
        }
    except Exception as e:
        db.rollback()
        print(f"Error creating guest house: {e}")
        raise HTTPException(status_code=500, detail="Failed to create guest house")

@router.put("/{guest_house_id}")
async def update_guest_house(
    guest_house_id: int,
    guest_house_data: GuestHouseCreate,
    db: Session = Depends(get_db)
):
    """Update an existing guest house"""
    try:
        guest_house = db.query(GuestHouse).filter(GuestHouse.id == guest_house_id).first()
        if not guest_house:
            raise HTTPException(status_code=404, detail="Guest house not found")
        
        # Update fields
        guest_house.name = guest_house_data.name
        guest_house.location = guest_house_data.location
        guest_house.address = guest_house_data.address
        guest_house.latitude = guest_house_data.latitude
        guest_house.longitude = guest_house_data.longitude
        guest_house.description = guest_house_data.description
        guest_house.contact_person = guest_house_data.contact_person
        guest_house.phone = guest_house_data.phone
        guest_house.email = guest_house_data.email
        guest_house.facilities = guest_house_data.facilities
        guest_house.house_rules = guest_house_data.house_rules
        guest_house.check_in_time = guest_house_data.check_in_time
        guest_house.check_out_time = guest_house_data.check_out_time
        
        db.commit()
        
        return {
            "id": guest_house.id,
            "name": guest_house.name,
            "message": "Guest house updated successfully"
        }
    except Exception as e:
        db.rollback()
        print(f"Error updating guest house: {e}")
        raise HTTPException(status_code=500, detail="Failed to update guest house")

@router.delete("/{guest_house_id}")
async def delete_guest_house(
    guest_house_id: int,
    db: Session = Depends(get_db)
):
    """Delete a guest house"""
    try:
        guest_house = db.query(GuestHouse).filter(GuestHouse.id == guest_house_id).first()
        if not guest_house:
            raise HTTPException(status_code=404, detail="Guest house not found")
        
        db.delete(guest_house)
        db.commit()
        
        return {"message": "Guest house deleted successfully"}
    except Exception as e:
        db.rollback()
        print(f"Error deleting guest house: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete guest house")