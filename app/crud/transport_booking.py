from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func
from typing import List, Optional, Dict, Any
from datetime import datetime
from app.models.transport_booking import TransportBooking, TransportStatusUpdate, TransportVendor
from app.models.event_participant import EventParticipant
from app.models.guesthouse import AccommodationAllocation
from app.models.welcome_package import ParticipantWelcomeDelivery, EventWelcomePackage
from app.schemas.transport_booking import (
    TransportBookingCreate, TransportBookingUpdate, 
    TransportStatusUpdateCreate, TransportVendorCreate
)

class CRUDTransportBooking:
    def create_booking(
        self, 
        db: Session, 
        booking: TransportBookingCreate, 
        created_by: str
    ) -> TransportBooking:
        """Create a new transport booking"""
        
        # Check if participants have welcome packages
        has_package = False
        package_location = None
        
        if booking.booking_type == "airport_pickup":
            package_check = self.check_welcome_packages(db, booking.participant_ids)
            if any(p["has_package"] for p in package_check):
                has_package = True
                package_location = "MSF Office - Main Building"
                # Add MSF office as first pickup location
                pickup_locations = [package_location] + booking.pickup_locations
            else:
                pickup_locations = booking.pickup_locations
        else:
            pickup_locations = booking.pickup_locations
        
        # Convert booking_type string to enum
        from app.models.transport_booking import BookingType, VendorType
        booking_type_enum = BookingType(booking.booking_type)
        vendor_type_enum = VendorType(booking.vendor_type)
        
        db_booking = TransportBooking(
            **booking.dict(exclude={"pickup_locations", "has_welcome_package", "package_pickup_location", "status", "booking_type", "vendor_type"}),
            booking_type=booking_type_enum,
            vendor_type=vendor_type_enum,
            pickup_locations=pickup_locations,
            has_welcome_package=has_package,
            package_pickup_location=package_location,
            status="pending",
            created_by=created_by
        )
        
        db.add(db_booking)
        db.commit()
        db.refresh(db_booking)
        
        # Create initial status update
        self.add_status_update(
            db, 
            db_booking.id, 
            TransportStatusUpdateCreate(
                status="pending",
                notes="Booking created"
            ),
            created_by
        )
        
        return db_booking
    
    def get_booking(self, db: Session, booking_id: int) -> Optional[TransportBooking]:
        """Get booking by ID with participant details"""
        booking = db.query(TransportBooking).filter(TransportBooking.id == booking_id).first()
        if booking:
            # Populate participant details
            participants = db.query(EventParticipant).filter(
                EventParticipant.id.in_(booking.participant_ids)
            ).all()
            
            booking.participants = [
                {
                    "id": p.id,
                    "name": p.full_name,
                    "email": p.email,
                    "phone": getattr(p, 'phone', None),
                    "role": p.role
                }
                for p in participants
            ]
            
            # Get event title if applicable
            if booking.event_id:
                from app.models.event import Event
                event = db.query(Event).filter(Event.id == booking.event_id).first()
                booking.event_title = event.title if event else None
        
        return booking
    
    def get_bookings(
        self, 
        db: Session, 
        skip: int = 0, 
        limit: int = 100,
        status: Optional[str] = None,
        booking_type: Optional[str] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None
    ) -> List[TransportBooking]:
        """Get bookings with filters"""
        query = db.query(TransportBooking)
        
        if status:
            query = query.filter(TransportBooking.status == status)
        if booking_type:
            query = query.filter(TransportBooking.booking_type == booking_type)
        if date_from:
            query = query.filter(TransportBooking.scheduled_time >= date_from)
        if date_to:
            query = query.filter(TransportBooking.scheduled_time <= date_to)
        
        bookings = query.offset(skip).limit(limit).all()
        
        # Populate participant details for each booking
        for booking in bookings:
            participants = db.query(EventParticipant).filter(
                EventParticipant.id.in_(booking.participant_ids)
            ).all()
            
            booking.participants = [
                {
                    "id": p.id,
                    "name": p.full_name,
                    "email": p.email,
                    "phone": getattr(p, 'phone', None),
                    "role": p.role
                }
                for p in participants
            ]
            
            # Get event title if applicable
            if booking.event_id:
                from app.models.event import Event
                event = db.query(Event).filter(Event.id == booking.event_id).first()
                booking.event_title = event.title if event else None
        
        return bookings
    
    def update_booking(
        self, 
        db: Session, 
        booking_id: int, 
        booking_update: TransportBookingUpdate,
        updated_by: str
    ) -> Optional[TransportBooking]:
        """Update booking"""
        booking = db.query(TransportBooking).filter(TransportBooking.id == booking_id).first()
        if not booking:
            return None
        
        update_data = booking_update.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(booking, field, value)
        
        # Add status update if status changed
        if "status" in update_data:
            self.add_status_update(
                db,
                booking_id,
                TransportStatusUpdateCreate(
                    status=update_data["status"],
                    notes=f"Status updated to {update_data['status']}"
                ),
                updated_by
            )
        
        db.commit()
        db.refresh(booking)
        return booking
    
    def delete_booking(self, db: Session, booking_id: int) -> bool:
        """Delete transport booking"""
        booking = db.query(TransportBooking).filter(TransportBooking.id == booking_id).first()
        if not booking:
            return False
        
        # Delete related status updates first
        db.query(TransportStatusUpdate).filter(TransportStatusUpdate.booking_id == booking_id).delete()
        
        # Delete the booking
        db.delete(booking)
        db.commit()
        return True
    
    def add_status_update(
        self,
        db: Session,
        booking_id: int,
        status_update: TransportStatusUpdateCreate,
        updated_by: str
    ) -> TransportStatusUpdate:
        """Add status update to booking"""
        db_update = TransportStatusUpdate(
            booking_id=booking_id,
            **status_update.dict(),
            updated_by=updated_by
        )
        
        # Update main booking status
        booking = db.query(TransportBooking).filter(TransportBooking.id == booking_id).first()
        if booking:
            booking.status = status_update.status
            
            # Update specific fields based on status
            if status_update.status == "package_collected":
                booking.package_collected = True
                booking.package_collected_at = datetime.utcnow()
                booking.package_collected_by = updated_by
            elif status_update.status == "visitor_picked_up":
                booking.visitor_picked_up = True
                booking.visitor_picked_up_at = datetime.utcnow()
            elif status_update.status == "completed":
                booking.completed_at = datetime.utcnow()
        
        db.add(db_update)
        db.commit()
        db.refresh(db_update)
        return db_update
    
    def get_status_updates(self, db: Session, booking_id: int) -> List[TransportStatusUpdate]:
        """Get all status updates for a booking"""
        return db.query(TransportStatusUpdate).filter(
            TransportStatusUpdate.booking_id == booking_id
        ).order_by(TransportStatusUpdate.created_at).all()
    
    def check_welcome_packages(self, db: Session, participant_ids: List[int]) -> List[Dict[str, Any]]:
        """Check if participants have welcome packages"""
        result = []
        
        for participant_id in participant_ids:
            # Get participant's event
            participant = db.query(EventParticipant).filter(
                EventParticipant.id == participant_id
            ).first()
            
            if not participant:
                result.append({
                    "participant_id": participant_id,
                    "has_package": False,
                    "package_items": []
                })
                continue
            
            # Check if event has welcome packages
            event_packages = db.query(EventWelcomePackage).filter(
                EventWelcomePackage.event_id == participant.event_id
            ).all()
            
            if not event_packages:
                result.append({
                    "participant_id": participant_id,
                    "has_package": False,
                    "package_items": []
                })
                continue
            
            # Check if participant has undelivered packages
            delivered_packages = db.query(ParticipantWelcomeDelivery).filter(
                and_(
                    ParticipantWelcomeDelivery.participant_id == participant_id,
                    ParticipantWelcomeDelivery.delivered == True
                )
            ).all()
            
            delivered_package_ids = {d.package_item_id for d in delivered_packages}
            undelivered_packages = [
                p for p in event_packages 
                if p.id not in delivered_package_ids
            ]
            
            result.append({
                "participant_id": participant_id,
                "has_package": len(undelivered_packages) > 0,
                "package_items": [p.item_name for p in undelivered_packages]
            })
        
        return result
    
    def suggest_booking_groups(
        self,
        db: Session,
        event_id: Optional[int] = None,
        booking_type: str = "airport_pickup",
        max_passengers: int = 4
    ) -> Dict[str, Any]:
        """Suggest booking groups based on accommodation and timing"""
        
        if event_id:
            participants = db.query(EventParticipant).filter(
                EventParticipant.event_id == event_id
            ).all()
        else:
            # Get all participants without existing bookings
            participants = db.query(EventParticipant).all()
        
        # Group by accommodation
        accommodation_groups = {}
        ungrouped = []
        
        for participant in participants:
            # Get participant's accommodation
            allocation = db.query(AccommodationAllocation).filter(
                AccommodationAllocation.participant_id == participant.id
            ).first()
            
            if allocation and allocation.room:
                location = allocation.room.guesthouse.name
            elif allocation and allocation.vendor_accommodation:
                location = allocation.vendor_accommodation.vendor_name
            else:
                location = "No accommodation"
            
            if location not in accommodation_groups:
                accommodation_groups[location] = []
            
            accommodation_groups[location].append({
                "id": participant.id,
                "name": participant.full_name or participant.name,
                "email": participant.email,
                "phone": participant.phone,
                "accommodation": location
            })
        
        # Create suggested groups
        suggested_groups = []
        for location, participants_list in accommodation_groups.items():
            # Split into groups of max_passengers
            for i in range(0, len(participants_list), max_passengers):
                group = participants_list[i:i + max_passengers]
                suggested_groups.append({
                    "pickup_location": location,
                    "participants": group,
                    "passenger_count": len(group)
                })
        
        return {
            "suggested_groups": suggested_groups,
            "ungrouped_participants": ungrouped
        }

# Vendor management
class CRUDTransportVendor:
    def create_vendor(
        self, 
        db: Session, 
        vendor: TransportVendorCreate, 
        created_by: str
    ) -> TransportVendor:
        """Create transport vendor"""
        db_vendor = TransportVendor(**vendor.dict(), created_by=created_by)
        db.add(db_vendor)
        db.commit()
        db.refresh(db_vendor)
        return db_vendor
    
    def get_vendors(self, db: Session, active_only: bool = True) -> List[TransportVendor]:
        """Get all transport vendors"""
        query = db.query(TransportVendor)
        if active_only:
            query = query.filter(TransportVendor.is_active == True)
        return query.all()
    
    def get_vendor(self, db: Session, vendor_id: int) -> Optional[TransportVendor]:
        """Get vendor by ID"""
        return db.query(TransportVendor).filter(TransportVendor.id == vendor_id).first()

# Create instances
transport_booking = CRUDTransportBooking()
transport_vendor = CRUDTransportVendor()
