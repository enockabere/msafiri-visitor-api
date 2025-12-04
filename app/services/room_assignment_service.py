from sqlalchemy.orm import Session
from app.models.guesthouse import AccommodationAllocation, VendorAccommodation
from app.models.event_participant import EventParticipant
from app.models.event import Event
import logging

logger = logging.getLogger(__name__)

def assign_room_with_sharing(db: Session, participant_id: int, event_id: int, tenant_id: int):
    """
    Assign room with intelligent sharing logic:
    1. Check for existing participants of same gender in same event
    2. If found and they have single room, convert to shared double room
    3. Otherwise assign single room
    
    🔥 CRITICAL: Uses the event's specifically selected hotel, not just any hotel
    """
    
    # Get participant details
    participant = db.query(EventParticipant).filter(
        EventParticipant.id == participant_id
    ).first()
    
    # Get event details to ensure we use the correct hotel
    event = db.query(Event).filter(Event.id == event_id).first()
    if not event or not event.vendor_accommodation_id:
        logger.error(f"Event {event_id} not found or has no vendor accommodation selected")
        return None
    
    logger.info(f"Assigning room for participant {participant_id} in event {event_id} using hotel ID {event.vendor_accommodation_id}")
    
    if not participant or not participant.gender:
        logger.warning(f"Participant {participant_id} not found or missing gender")
        return create_single_room_allocation(db, participant_id, event_id, tenant_id)
    
    # 🔥 CRITICAL FIX: Find other participants of same gender in same event AND same hotel with single rooms
    same_gender_participants = db.query(AccommodationAllocation).join(
        EventParticipant, AccommodationAllocation.participant_id == EventParticipant.id
    ).filter(
        AccommodationAllocation.event_id == event_id,
        AccommodationAllocation.vendor_accommodation_id == event.vendor_accommodation_id,  # 🔥 ENSURE SAME HOTEL
        AccommodationAllocation.status.in_(['booked', 'checked_in']),
        AccommodationAllocation.room_type == 'single',
        AccommodationAllocation.number_of_guests == 1,
        EventParticipant.gender == participant.gender,
        AccommodationAllocation.participant_id != participant_id
    ).first()
    
    if same_gender_participants:
        # Convert existing single room to shared double room
        logger.info(f"Converting single room to shared for participants {same_gender_participants.participant_id} and {participant_id}")
        
        # Update existing allocation to double room with 2 guests
        same_gender_participants.room_type = 'double'
        same_gender_participants.number_of_guests = 2
        same_gender_participants.notes = f"Shared with participant {participant_id} ({participant.full_name})"
        
        # Create new allocation for current participant sharing the same room
        new_allocation = AccommodationAllocation(
            tenant_id=tenant_id,
            accommodation_type='vendor',
            participant_id=participant_id,
            event_id=event_id,
            vendor_accommodation_id=same_gender_participants.vendor_accommodation_id,
            guest_name=participant.full_name,
            guest_email=participant.email,
            check_in_date=same_gender_participants.check_in_date,
            check_out_date=same_gender_participants.check_out_date,
            number_of_guests=2,
            room_type='double',
            status='booked',
            notes=f"Shared with participant {same_gender_participants.participant_id}"
        )
        
        db.add(new_allocation)
        db.commit()
        
        logger.info(f"Created shared double room allocation for participant {participant_id}")
        return new_allocation
    
    else:
        # No same-gender participant found, create single room
        return create_single_room_allocation(db, participant_id, event_id, tenant_id)

def create_single_room_allocation(db: Session, participant_id: int, event_id: int, tenant_id: int):
    """Create a single room allocation"""
    
    participant = db.query(EventParticipant).filter(
        EventParticipant.id == participant_id
    ).first()
    
    event = db.query(Event).filter(Event.id == event_id).first()
    
    # 🔥 CRITICAL FIX: Use the event's specific vendor accommodation, not just any vendor
    vendor_accommodation = None
    if event and event.vendor_accommodation_id:
        vendor_accommodation = db.query(VendorAccommodation).filter(
            VendorAccommodation.id == event.vendor_accommodation_id,
            VendorAccommodation.tenant_id == tenant_id
        ).first()
        logger.info(f"Using event's selected hotel: {vendor_accommodation.vendor_name if vendor_accommodation else 'NOT FOUND'}")
    
    if not vendor_accommodation:
        logger.error(f"No vendor accommodation found for event {event_id}. Event vendor_accommodation_id: {event.vendor_accommodation_id if event else 'NO EVENT'}")
        return None
    
    new_allocation = AccommodationAllocation(
        tenant_id=tenant_id,
        accommodation_type='vendor',
        participant_id=participant_id,
        event_id=event_id,
        vendor_accommodation_id=vendor_accommodation.id,
        guest_name=participant.full_name,
        guest_email=participant.email,
        check_in_date=event.start_date,
        check_out_date=event.end_date,
        number_of_guests=1,
        room_type='single',
        status='booked'
    )
    
    db.add(new_allocation)
    db.commit()
    
    logger.info(f"Created single room allocation for participant {participant_id}")
    return new_allocation

def handle_room_cancellation(db: Session, participant_id: int):
    """
    Handle room cancellation with sharing logic:
    1. If participant was in shared room, convert roommate to single
    2. If participant was in single room, just cancel
    """
    
    # Find the allocation to cancel
    allocation = db.query(AccommodationAllocation).filter(
        AccommodationAllocation.participant_id == participant_id,
        AccommodationAllocation.status.in_(['booked', 'checked_in'])
    ).first()
    
    if not allocation:
        logger.warning(f"No active allocation found for participant {participant_id}")
        return
    
    if allocation.room_type == 'double' and allocation.number_of_guests == 2:
        # Find roommate and convert to single
        roommate_allocation = db.query(AccommodationAllocation).filter(
            AccommodationAllocation.event_id == allocation.event_id,
            AccommodationAllocation.vendor_accommodation_id == allocation.vendor_accommodation_id,
            AccommodationAllocation.room_type == 'double',
            AccommodationAllocation.number_of_guests == 2,
            AccommodationAllocation.participant_id != participant_id,
            AccommodationAllocation.status.in_(['booked', 'checked_in'])
        ).first()
        
        if roommate_allocation:
            # Convert roommate to single room
            roommate_allocation.room_type = 'single'
            roommate_allocation.number_of_guests = 1
            roommate_allocation.notes = f"Converted to single room after participant {participant_id} cancelled"
            
            logger.info(f"Converted roommate {roommate_allocation.participant_id} to single room")
    
    # Cancel the original allocation
    db.delete(allocation)
    db.commit()
    
    logger.info(f"Cancelled accommodation for participant {participant_id}")