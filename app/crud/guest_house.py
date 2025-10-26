from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from app.models.guest_house import GuestHouse, GuestHouseRoom, GuestHouseBooking
from app.models.event_participant import EventParticipant
from app.models.event import Event
from app.models.accommodation import RoomAssignment
from app.schemas.guest_house import (
    GuestHouseCreate, GuestHouseUpdate,
    GuestHouseRoomCreate, GuestHouseRoomUpdate,
    GuestHouseBookingCreate, GuestHouseBookingUpdate
)

class GuestHouseCRUD:
    def create_guest_house(self, db: Session, guest_house: GuestHouseCreate, created_by: str) -> GuestHouse:
        db_guest_house = GuestHouse(
            **guest_house.dict(),
            created_by=created_by
        )
        db.add(db_guest_house)
        db.commit()
        db.refresh(db_guest_house)
        return db_guest_house

    def get_guest_houses(self, db: Session, tenant_id: str, active_only: bool = True) -> List[GuestHouse]:
        query = db.query(GuestHouse).filter(GuestHouse.tenant_id == tenant_id)
        if active_only:
            query = query.filter(GuestHouse.is_active == True)
        return query.all()

    def get_guest_house(self, db: Session, guest_house_id: int) -> Optional[GuestHouse]:
        return db.query(GuestHouse).filter(GuestHouse.id == guest_house_id).first()

    def update_guest_house(self, db: Session, guest_house_id: int, guest_house_update: GuestHouseUpdate) -> Optional[GuestHouse]:
        db_guest_house = self.get_guest_house(db, guest_house_id)
        if not db_guest_house:
            return None
        
        update_data = guest_house_update.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_guest_house, field, value)
        
        db.commit()
        db.refresh(db_guest_house)
        return db_guest_house

    def delete_guest_house(self, db: Session, guest_house_id: int) -> bool:
        db_guest_house = self.get_guest_house(db, guest_house_id)
        if not db_guest_house:
            return False
        
        # Check if there are active bookings
        active_bookings = db.query(GuestHouseBooking).filter(
            GuestHouseBooking.guest_house_id == guest_house_id,
            GuestHouseBooking.status.in_(["booked", "checked_in"])
        ).count()
        
        if active_bookings > 0:
            # Soft delete - just deactivate
            db_guest_house.is_active = False
            db.commit()
        else:
            # Hard delete if no active bookings
            db.delete(db_guest_house)
            db.commit()
        
        return True

class GuestHouseRoomCRUD:
    def create_room(self, db: Session, room: GuestHouseRoomCreate, created_by: str) -> GuestHouseRoom:
        db_room = GuestHouseRoom(
            **room.dict(),
            created_by=created_by
        )
        db.add(db_room)
        db.commit()
        db.refresh(db_room)
        return db_room

    def get_rooms(self, db: Session, guest_house_id: int, active_only: bool = True) -> List[GuestHouseRoom]:
        query = db.query(GuestHouseRoom).filter(GuestHouseRoom.guest_house_id == guest_house_id)
        if active_only:
            query = query.filter(GuestHouseRoom.is_active == True)
        return query.all()

    def get_room(self, db: Session, room_id: int) -> Optional[GuestHouseRoom]:
        return db.query(GuestHouseRoom).filter(GuestHouseRoom.id == room_id).first()

    def update_room(self, db: Session, room_id: int, room_update: GuestHouseRoomUpdate) -> Optional[GuestHouseRoom]:
        db_room = self.get_room(db, room_id)
        if not db_room:
            return None
        
        update_data = room_update.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_room, field, value)
        
        db.commit()
        db.refresh(db_room)
        return db_room

    def check_room_availability(self, db: Session, room_id: int, check_in: datetime, check_out: datetime, exclude_booking_id: Optional[int] = None) -> bool:
        query = db.query(GuestHouseBooking).filter(
            GuestHouseBooking.room_id == room_id,
            GuestHouseBooking.status.in_(["booked", "checked_in"]),
            or_(
                and_(GuestHouseBooking.check_in_date <= check_in, GuestHouseBooking.check_out_date > check_in),
                and_(GuestHouseBooking.check_in_date < check_out, GuestHouseBooking.check_out_date >= check_out),
                and_(GuestHouseBooking.check_in_date >= check_in, GuestHouseBooking.check_out_date <= check_out)
            )
        )
        
        if exclude_booking_id:
            query = query.filter(GuestHouseBooking.id != exclude_booking_id)
        
        conflicting_bookings = query.count()
        return conflicting_bookings == 0

class GuestHouseBookingCRUD:
    def create_booking(self, db: Session, booking: GuestHouseBookingCreate, booked_by: str) -> GuestHouseBooking:
        # Generate booking reference
        booking_ref = f"GH{booking.guest_house_id:03d}{booking.room_id:03d}{datetime.now().strftime('%Y%m%d%H%M')}"
        
        db_booking = GuestHouseBooking(
            **booking.dict(),
            booked_by=booked_by,
            booking_reference=booking_ref
        )
        db.add(db_booking)
        db.commit()
        db.refresh(db_booking)
        return db_booking

    def get_bookings(self, db: Session, tenant_id: str, participant_id: Optional[int] = None, 
                    guest_house_id: Optional[int] = None, status: Optional[str] = None) -> List[Dict[str, Any]]:
        query = db.query(
            GuestHouseBooking,
            GuestHouse.name.label("guest_house_name"),
            GuestHouseRoom.room_number,
            EventParticipant.full_name.label("participant_name"),
            EventParticipant.email.label("participant_email"),
            Event.title.label("event_title")
        ).join(
            GuestHouse, GuestHouseBooking.guest_house_id == GuestHouse.id
        ).join(
            GuestHouseRoom, GuestHouseBooking.room_id == GuestHouseRoom.id
        ).join(
            EventParticipant, GuestHouseBooking.participant_id == EventParticipant.id
        ).join(
            Event, EventParticipant.event_id == Event.id
        ).filter(
            GuestHouse.tenant_id == tenant_id
        )
        
        if participant_id:
            query = query.filter(GuestHouseBooking.participant_id == participant_id)
        
        if guest_house_id:
            query = query.filter(GuestHouseBooking.guest_house_id == guest_house_id)
        
        if status:
            query = query.filter(GuestHouseBooking.status == status)
        
        results = query.all()
        
        bookings = []
        for result in results:
            booking = result.GuestHouseBooking
            bookings.append({
                "id": booking.id,
                "guest_house_id": booking.guest_house_id,
                "room_id": booking.room_id,
                "participant_id": booking.participant_id,
                "check_in_date": booking.check_in_date,
                "check_out_date": booking.check_out_date,
                "number_of_guests": booking.number_of_guests,
                "status": booking.status,
                "checked_in": booking.checked_in,
                "checked_in_at": booking.checked_in_at,
                "checked_out": booking.checked_out,
                "checked_out_at": booking.checked_out_at,
                "special_requests": booking.special_requests,
                "admin_notes": booking.admin_notes,
                "booked_by": booking.booked_by,
                "booking_reference": booking.booking_reference,
                "created_at": booking.created_at,
                "guest_house_name": result.guest_house_name,
                "room_number": result.room_number,
                "participant": {
                    "id": booking.participant_id,
                    "full_name": result.participant_name,
                    "email": result.participant_email,
                    "event_title": result.event_title
                }
            })
        
        return bookings

    def get_booking(self, db: Session, booking_id: int) -> Optional[GuestHouseBooking]:
        return db.query(GuestHouseBooking).filter(GuestHouseBooking.id == booking_id).first()

    def update_booking(self, db: Session, booking_id: int, booking_update: GuestHouseBookingUpdate) -> Optional[GuestHouseBooking]:
        db_booking = self.get_booking(db, booking_id)
        if not db_booking:
            return None
        
        update_data = booking_update.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_booking, field, value)
        
        db.commit()
        db.refresh(db_booking)
        return db_booking

    def check_participant_conflicts(self, db: Session, participant_id: int, check_in: datetime, check_out: datetime, exclude_booking_id: Optional[int] = None) -> Dict[str, Any]:
        # Check guest house bookings
        gh_query = db.query(GuestHouseBooking).filter(
            GuestHouseBooking.participant_id == participant_id,
            GuestHouseBooking.status.in_(["booked", "checked_in"]),
            or_(
                and_(GuestHouseBooking.check_in_date <= check_in, GuestHouseBooking.check_out_date > check_in),
                and_(GuestHouseBooking.check_in_date < check_out, GuestHouseBooking.check_out_date >= check_out),
                and_(GuestHouseBooking.check_in_date >= check_in, GuestHouseBooking.check_out_date <= check_out)
            )
        )
        
        if exclude_booking_id:
            gh_query = gh_query.filter(GuestHouseBooking.id != exclude_booking_id)
        
        # Check vendor hotel bookings
        vendor_query = db.query(RoomAssignment).filter(
            RoomAssignment.participant_id == participant_id,
            or_(
                and_(RoomAssignment.check_in_date <= check_in, RoomAssignment.check_out_date > check_in),
                and_(RoomAssignment.check_in_date < check_out, RoomAssignment.check_out_date >= check_out),
                and_(RoomAssignment.check_in_date >= check_in, RoomAssignment.check_out_date <= check_out)
            )
        )
        
        gh_conflicts = gh_query.all()
        vendor_conflicts = vendor_query.all()
        
        conflicts = []
        
        for booking in gh_conflicts:
            conflicts.append({
                "type": "guest_house",
                "id": booking.id,
                "check_in_date": booking.check_in_date.isoformat(),
                "check_out_date": booking.check_out_date.isoformat(),
                "location": f"Guest House Booking #{booking.id}"
            })
        
        for assignment in vendor_conflicts:
            conflicts.append({
                "type": "vendor_hotel",
                "id": assignment.id,
                "check_in_date": assignment.check_in_date.isoformat(),
                "check_out_date": assignment.check_out_date.isoformat(),
                "location": f"{assignment.hotel_name} - Room {assignment.room_number}"
            })
        
        return {
            "has_conflicts": len(conflicts) > 0,
            "conflicting_bookings": conflicts
        }

    def get_participant_first_accommodation(self, db: Session, participant_id: int) -> Optional[Dict[str, Any]]:
        """Get the earliest accommodation booking for a participant"""
        # Get guest house bookings
        gh_bookings = db.query(
            GuestHouseBooking,
            GuestHouse.name.label("location_name"),
            GuestHouse.address
        ).join(
            GuestHouse, GuestHouseBooking.guest_house_id == GuestHouse.id
        ).filter(
            GuestHouseBooking.participant_id == participant_id,
            GuestHouseBooking.status.in_(["booked", "checked_in"])
        ).all()
        
        # Get vendor hotel bookings
        vendor_bookings = db.query(RoomAssignment).filter(
            RoomAssignment.participant_id == participant_id
        ).all()
        
        all_accommodations = []
        
        for booking in gh_bookings:
            all_accommodations.append({
                "type": "guest_house",
                "check_in_date": booking.GuestHouseBooking.check_in_date,
                "location": booking.location_name,
                "address": booking.address
            })
        
        for assignment in vendor_bookings:
            all_accommodations.append({
                "type": "vendor_hotel",
                "check_in_date": assignment.check_in_date,
                "location": assignment.hotel_name,
                "address": assignment.address
            })
        
        if not all_accommodations:
            return None
        
        # Sort by check-in date and return the earliest
        all_accommodations.sort(key=lambda x: x["check_in_date"])
        return all_accommodations[0]

# Create instances
guest_house_crud = GuestHouseCRUD()
guest_house_room_crud = GuestHouseRoomCRUD()
guest_house_booking_crud = GuestHouseBookingCRUD()