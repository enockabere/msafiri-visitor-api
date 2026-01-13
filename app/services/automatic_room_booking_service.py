from sqlalchemy.orm import Session
from app.models.guesthouse import AccommodationAllocation, VendorEventAccommodation
from app.models.event_participant import EventParticipant
from app.models.event import Event
from sqlalchemy import text
import logging

logger = logging.getLogger(__name__)

def refresh_automatic_room_booking(db: Session, event_id: int, tenant_id: int):
    """
    Refresh automatic room booking for an event based on updated room configuration.
    This function reassigns participants to rooms based on the new single/double room allocation.
    """
    
    logger.info(f"🔄 Starting automatic room booking refresh for event {event_id}")
    
    try:
        # Get event details
        event = db.query(Event).filter(Event.id == event_id).first()
        if not event:
            logger.error(f"❌ Event {event_id} not found")
            return False
        
        # Get vendor event accommodation setup
        vendor_setup = db.query(VendorEventAccommodation).filter(
            VendorEventAccommodation.event_id == event_id,
            VendorEventAccommodation.tenant_id == tenant_id,
            VendorEventAccommodation.is_active == True
        ).first()
        
        if not vendor_setup:
            logger.warning(f"⚠️ No vendor event accommodation setup found for event {event_id}")
            return False
        
        logger.info(f"📊 Current setup: {vendor_setup.single_rooms} single, {vendor_setup.double_rooms} double rooms")
        
        # Get all confirmed participants for this event who want to stay at venue
        confirmed_participants = db.query(EventParticipant).filter(
            EventParticipant.event_id == event_id,
            EventParticipant.status == "confirmed",
            EventParticipant.accommodation_preference == "staying_at_venue"
        ).all()
        
        logger.info(f"👥 Found {len(confirmed_participants)} confirmed participants")
        
        if not confirmed_participants:
            logger.info(f"✅ No confirmed participants to assign rooms")
            return True
        
        # Cancel existing vendor accommodation allocations for this event
        existing_allocations = db.query(AccommodationAllocation).filter(
            AccommodationAllocation.event_id == event_id,
            AccommodationAllocation.accommodation_type == "vendor",
            AccommodationAllocation.status.in_(["booked", "checked_in"])
        ).all()
        
        logger.info(f"🗑️ Cancelling {len(existing_allocations)} existing allocations")
        for allocation in existing_allocations:
            db.delete(allocation)
        
        # Reset current occupants
        vendor_setup.current_occupants = 0
        
        # Group participants by gender for room sharing
        participants_by_gender = {}
        for participant in confirmed_participants:
            # Get gender from public_registrations table (most reliable source)
            gender_result = db.execute(text(
                "SELECT gender_identity FROM public_registrations WHERE participant_id = :participant_id"
            ), {"participant_id": participant.id}).fetchone()
            
            participant_gender = None
            if gender_result and gender_result[0]:
                participant_gender = gender_result[0]
            else:
                # Fallback to participant table fields
                participant_gender = participant.gender_identity or participant.sex or participant.gender
            
            if not participant_gender:
                logger.warning(f"Participant {participant.id} ({participant.full_name}) missing gender information, skipping")
                continue
            
            # Normalize gender values
            gender = "other"  # Default
            gender_lower = participant_gender.lower()
            if gender_lower in ['man', 'male']:
                gender = 'male'
            elif gender_lower in ['woman', 'female']:
                gender = 'female'
            
            if gender not in participants_by_gender:
                participants_by_gender[gender] = []
            participants_by_gender[gender].append(participant)
        
        logger.info(f"👥 Participants by gender: {[(g, len(p)) for g, p in participants_by_gender.items()]}")
        
        # Assign rooms based on new configuration
        rooms_used = {"single": 0, "double": 0}
        
        # Strategy: Prioritize double rooms for same-gender pairs, then single rooms
        for gender, participants in participants_by_gender.items():
            logger.info(f"🏠 Assigning rooms for {len(participants)} {gender} participants")
            
            # For non-binary genders, only assign single rooms
            if gender == "other":
                for participant in participants:
                    if rooms_used["single"] < vendor_setup.single_rooms:
                        success = _create_room_allocation(
                            db, participant, event, vendor_setup, "single", 1
                        )
                        if success:
                            rooms_used["single"] += 1
                            vendor_setup.current_occupants += 1
                        else:
                            logger.error(f"❌ Failed to assign single room to {participant.full_name}")
                    else:
                        logger.warning(f"⚠️ No single rooms available for {participant.full_name}")
                continue
            
            # For male/female participants, try to pair them in double rooms first
            participants_list = participants.copy()
            
            # Assign double rooms (2 people per room)
            while len(participants_list) >= 2 and rooms_used["double"] < vendor_setup.double_rooms:
                participant1 = participants_list.pop(0)
                participant2 = participants_list.pop(0)
                
                # Create allocations for both participants sharing a double room
                success1 = _create_room_allocation(
                    db, participant1, event, vendor_setup, "double", 2,
                    roommate_name=participant2.full_name
                )
                success2 = _create_room_allocation(
                    db, participant2, event, vendor_setup, "double", 2,
                    roommate_name=participant1.full_name
                )
                
                if success1 and success2:
                    rooms_used["double"] += 1
                    vendor_setup.current_occupants += 2
                    logger.info(f"🏠 Assigned double room to {participant1.full_name} and {participant2.full_name}")
                else:
                    logger.error(f"❌ Failed to assign double room to {participant1.full_name} and {participant2.full_name}")
            
            # Assign remaining participants to single rooms
            for participant in participants_list:
                if rooms_used["single"] < vendor_setup.single_rooms:
                    success = _create_room_allocation(
                        db, participant, event, vendor_setup, "single", 1
                    )
                    if success:
                        rooms_used["single"] += 1
                        vendor_setup.current_occupants += 1
                        logger.info(f"🏠 Assigned single room to {participant.full_name}")
                    else:
                        logger.error(f"❌ Failed to assign single room to {participant.full_name}")
                else:
                    logger.warning(f"⚠️ No single rooms available for {participant.full_name}")
        
        db.commit()
        
        logger.info(f"✅ Room booking refresh completed for event {event_id}")
        logger.info(f"📊 Rooms used: {rooms_used['single']} single, {rooms_used['double']} double")
        logger.info(f"👥 Total occupants: {vendor_setup.current_occupants}")
        
        return True
        
    except Exception as e:
        logger.error(f"💥 Error refreshing room booking for event {event_id}: {str(e)}")
        db.rollback()
        return False

def _create_room_allocation(db: Session, participant: EventParticipant, event: Event, 
                          vendor_setup: VendorEventAccommodation, room_type: str, 
                          number_of_guests: int, roommate_name: str = None):
    """Create a room allocation for a participant"""
    
    try:
        notes = f"Auto-assigned {room_type} room"
        if roommate_name:
            notes += f" (shared with {roommate_name})"
        
        allocation = AccommodationAllocation(
            tenant_id=event.tenant_id,
            accommodation_type="vendor",
            participant_id=participant.id,
            event_id=event.id,
            vendor_accommodation_id=vendor_setup.vendor_accommodation_id,
            guest_name=participant.full_name,
            guest_email=participant.email,
            check_in_date=event.start_date,
            check_out_date=event.end_date,
            number_of_guests=number_of_guests,
            room_type=room_type,
            status="booked",
            notes=notes
        )
        
        db.add(allocation)
        return True
        
    except Exception as e:
        logger.error(f"💥 Error creating room allocation for {participant.full_name}: {str(e)}")
        return False