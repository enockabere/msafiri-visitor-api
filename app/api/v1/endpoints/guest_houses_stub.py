from fastapi import APIRouter, HTTPException, Depends, Query
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.models.guesthouse import GuestHouse
from pydantic import BaseModel
from typing import Optional, Dict, Any
import json

router = APIRouter()

class GuestHouseCreate(BaseModel):
    name: str
    location: str
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    description: Optional[str] = None
    facilities: Optional[Dict[str, Any]] = None
    house_rules: Optional[str] = None
    tenant_id: str

@router.get("/")
async def get_guest_houses(
    tenant_context: str = Query(...),
    db: Session = Depends(get_db)
):
    """Get all guest houses for a tenant"""
    try:
        print(f"🔍 [DEBUG] Guest house API called with tenant_context: {tenant_context}")
        
        # Convert tenant slug to tenant ID
        from app.models.tenant import Tenant
        tenant = db.query(Tenant).filter(Tenant.slug == tenant_context).first()
        print(f"🔍 [DEBUG] Found tenant: {tenant.name if tenant else 'None'} (ID: {tenant.id if tenant else 'None'})")
        
        if not tenant:
            print(f"🔍 [DEBUG] No tenant found for slug: {tenant_context}")
            return []
        
        guest_houses = db.query(GuestHouse).filter(
            GuestHouse.tenant_id == tenant.id
        ).all()
        print(f"🔍 [DEBUG] Found {len(guest_houses)} guest houses for tenant ID {tenant.id}")
        
        result = []
        for gh in guest_houses:
            print(f"🔍 [DEBUG] Processing guest house: {gh.name} (ID: {gh.id})")
            try:
                facilities = json.loads(gh.facilities) if gh.facilities else {}
            except Exception as facility_error:
                print(f"🔍 [DEBUG] Error parsing facilities for {gh.name}: {facility_error}")
                facilities = {}
            
            house_data = {
                "id": gh.id,
                "name": gh.name,
                "location": gh.location,
                "address": gh.address or "",
                "latitude": gh.latitude,
                "longitude": gh.longitude,
                "description": gh.description,
                "contact_person": gh.contact_person,
                "phone": gh.phone,
                "email": gh.email,
                "facilities": facilities,
                "house_rules": gh.house_rules,
                "check_in_time": gh.check_in_time,
                "check_out_time": gh.check_out_time,
                "is_active": gh.is_active,
                "tenant_id": gh.tenant_id,
                "created_by": gh.created_by,
                "created_at": gh.created_at.isoformat() if gh.created_at else None,
                "rooms": [{
                    "id": room.id,
                    "room_number": room.room_number,
                    "capacity": room.capacity,
                    "room_type": room.room_type,
                    "description": room.description,
                    "is_active": room.is_active
                } for room in gh.rooms]
            }
            result.append(house_data)
            print(f"🔍 [DEBUG] Added house data: {house_data['name']} with {len(house_data['rooms'])} rooms")
        
        print(f"🔍 [DEBUG] Returning {len(result)} guest houses")
        return result
    except Exception as e:
        print(f"🔍 [DEBUG] Error fetching guest houses: {e}")
        import traceback
        traceback.print_exc()
        return []

@router.post("/")
async def create_guest_house(
    guest_house_data: GuestHouseCreate,
    db: Session = Depends(get_db)
):
    """Create a new guest house"""
    try:
        # Convert tenant slug to tenant ID
        from app.models.tenant import Tenant
        tenant = db.query(Tenant).filter(Tenant.slug == guest_house_data.tenant_id).first()
        if not tenant:
            raise HTTPException(status_code=404, detail="Tenant not found")
        
        new_guest_house = GuestHouse(
            name=guest_house_data.name,
            location=guest_house_data.location,
            address="",  # Not used in simplified form
            latitude=guest_house_data.latitude,
            longitude=guest_house_data.longitude,
            description=guest_house_data.description,
            tenant_id=tenant.id,  # Use tenant ID instead of slug
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
        guest_house.latitude = guest_house_data.latitude
        guest_house.longitude = guest_house_data.longitude
        guest_house.description = guest_house_data.description
        guest_house.facilities = guest_house_data.facilities
        guest_house.house_rules = guest_house_data.house_rules
        
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