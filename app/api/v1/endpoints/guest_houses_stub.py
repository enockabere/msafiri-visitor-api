from fastapi import APIRouter, HTTPException, Depends, Query
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.models.guesthouse import GuestHouse, Room
from pydantic import BaseModel
from typing import Optional, Dict, Any
import json

router = APIRouter()

class GuestHouseCreate(BaseModel):
    name: str
    location: str
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    facilities: Optional[Dict[str, Any]] = None
    house_rules: Optional[str] = None
    tenant_id: str

class GuestHouseUpdate(BaseModel):
    is_active: Optional[bool] = None
    name: Optional[str] = None
    location: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    facilities: Optional[Dict[str, Any]] = None
    house_rules: Optional[str] = None

class RoomCreate(BaseModel):
    room_number: str
    room_name: Optional[str] = None
    capacity: int
    room_type: Optional[str] = None
    facilities: Optional[Dict[str, Any]] = None

class RoomUpdate(BaseModel):
    room_number: Optional[str] = None
    room_name: Optional[str] = None
    capacity: Optional[int] = None
    room_type: Optional[str] = None
    facilities: Optional[Dict[str, Any]] = None
    is_active: Optional[bool] = None

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
                "rooms": []
            }
            
            # Get room data with occupancy information
            for room in gh.rooms:
                # Get current occupants and their genders
                from app.models.guesthouse import AccommodationAllocation
                from sqlalchemy import text
                
                allocations = db.query(AccommodationAllocation).filter(
                    AccommodationAllocation.room_id == room.id,
                    AccommodationAllocation.status.in_(["booked", "checked_in"])
                ).all()
                
                current_occupants = len(allocations)
                occupant_genders = []
                
                for allocation in allocations:
                    if allocation.participant_id:
                        gender_result = db.execute(text(
                            "SELECT gender_identity FROM public_registrations WHERE participant_id = :participant_id"
                        ), {"participant_id": allocation.participant_id}).fetchone()
                        
                        if gender_result and gender_result[0]:
                            reg_gender = gender_result[0].lower()
                            if reg_gender in ['man', 'male']:
                                occupant_genders.append('male')
                            elif reg_gender in ['woman', 'female']:
                                occupant_genders.append('female')
                            else:
                                occupant_genders.append('other')
                
                # Remove duplicates
                occupant_genders = list(set(occupant_genders))
                
                room_data = {
                    "id": room.id,
                    "room_number": room.room_number,
                    "capacity": room.capacity,
                    "room_type": room.room_type,
                    "is_active": room.is_active,
                    "current_occupants": current_occupants,
                    "occupant_genders": occupant_genders
                }
                house_data["rooms"].append(room_data)
            
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
            facilities=json.dumps(guest_house_data.facilities) if guest_house_data.facilities else None,
            house_rules=guest_house_data.house_rules,
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
    guest_house_data: GuestHouseUpdate,
    db: Session = Depends(get_db)
):
    """Update an existing guest house (partial update)"""
    try:
        guest_house = db.query(GuestHouse).filter(GuestHouse.id == guest_house_id).first()
        if not guest_house:
            raise HTTPException(status_code=404, detail="Guest house not found")
        
        # Update only provided fields
        if guest_house_data.is_active is not None:
            guest_house.is_active = guest_house_data.is_active
        if guest_house_data.name is not None:
            guest_house.name = guest_house_data.name
        if guest_house_data.location is not None:
            guest_house.location = guest_house_data.location
        if guest_house_data.latitude is not None:
            guest_house.latitude = guest_house_data.latitude
        if guest_house_data.longitude is not None:
            guest_house.longitude = guest_house_data.longitude

        if guest_house_data.facilities is not None:
            guest_house.facilities = json.dumps(guest_house_data.facilities)
        if guest_house_data.house_rules is not None:
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

# Room Management Endpoints
@router.get("/{guest_house_id}/rooms")
async def get_rooms(
    guest_house_id: int,
    db: Session = Depends(get_db)
):
    """Get all rooms for a guest house"""
    try:
        guest_house = db.query(GuestHouse).filter(GuestHouse.id == guest_house_id).first()
        if not guest_house:
            raise HTTPException(status_code=404, detail="Guest house not found")
        
        rooms = db.query(Room).filter(Room.guesthouse_id == guest_house_id).all()
        
        result = []
        for room in rooms:
            try:
                facilities = json.loads(room.amenities) if room.amenities else {}
            except:
                facilities = {}
            
            result.append({
                "id": room.id,
                "room_number": room.room_number,
                "capacity": room.capacity,
                "room_type": room.room_type,
                "facilities": facilities,
                "is_active": room.is_active
            })
        
        return result
    except Exception as e:
        print(f"Error fetching rooms: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch rooms")

@router.post("/{guest_house_id}/rooms")
async def create_room(
    guest_house_id: int,
    room_data: RoomCreate,
    db: Session = Depends(get_db)
):
    """Create a new room"""
    try:
        guest_house = db.query(GuestHouse).filter(GuestHouse.id == guest_house_id).first()
        if not guest_house:
            raise HTTPException(status_code=404, detail="Guest house not found")
        
        new_room = Room(
            guesthouse_id=guest_house_id,
            tenant_id=guest_house.tenant_id,
            room_number=room_data.room_number,
            capacity=room_data.capacity,
            room_type=room_data.room_type or "single",
            amenities=json.dumps(room_data.facilities) if room_data.facilities else None,
            is_active=True
        )
        
        db.add(new_room)
        db.commit()
        db.refresh(new_room)
        
        return {
            "id": new_room.id,
            "room_number": new_room.room_number,
            "message": "Room created successfully"
        }
    except Exception as e:
        db.rollback()
        print(f"Error creating room: {e}")
        raise HTTPException(status_code=500, detail="Failed to create room")

@router.put("/rooms/{room_id}")
async def update_room(
    room_id: int,
    room_data: RoomUpdate,
    db: Session = Depends(get_db)
):
    """Update a room"""
    try:
        room = db.query(Room).filter(Room.id == room_id).first()
        if not room:
            raise HTTPException(status_code=404, detail="Room not found")
        
        # Update only provided fields
        if room_data.room_number is not None:
            room.room_number = room_data.room_number
        if room_data.capacity is not None:
            room.capacity = room_data.capacity
        if room_data.room_type is not None:
            room.room_type = room_data.room_type

        if room_data.facilities is not None:
            room.amenities = json.dumps(room_data.facilities)
        if room_data.is_active is not None:
            room.is_active = room_data.is_active
        
        db.commit()
        
        return {
            "id": room.id,
            "room_number": room.room_number,
            "message": "Room updated successfully"
        }
    except Exception as e:
        db.rollback()
        print(f"Error updating room: {e}")
        raise HTTPException(status_code=500, detail="Failed to update room")