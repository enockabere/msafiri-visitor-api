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
        
        # Separate facilitators/organizers from visitors
        # Facilitators/organizers always get single rooms
        facilitators = []
        visitors_by_gender = {"male": [], "female": [], "other": []}

        for participant in confirmed_participants:
            # Get gender from event_participants first (most reliable), then fallback to public_registrations
            gender_result = db.execute(text("""
                SELECT COALESCE(ep.gender_identity, pr.gender_identity) as gender
                FROM event_participants ep
                LEFT JOIN public_registrations pr ON ep.id = pr.participant_id
                WHERE ep.id = :participant_id
            """), {"participant_id": participant.id}).fetchone()

            participant_gender = gender_result[0] if gender_result and gender_result[0] else None

            # Check if participant is facilitator/organizer - they get single rooms
            # Check both role and participant_role fields - if EITHER says facilitator/organizer, they get single room
            participant_role_value = (participant.participant_role or '').lower()
            role_value = (participant.role or '').lower()
            is_facilitator = participant_role_value in ['facilitator', 'organizer'] or role_value in ['facilitator', 'organizer']
            if is_facilitator:
                facilitators.append(participant)
                continue

            if not participant_gender:
                logger.warning(f"Participant {participant.id} ({participant.full_name}) missing gender information, assigning to 'other'")
                visitors_by_gender["other"].append(participant)
                continue

            # Normalize gender values
            gender = "other"  # Default
            gender_lower = participant_gender.lower()
            if gender_lower in ['man', 'male']:
                gender = 'male'
            elif gender_lower in ['woman', 'female']:
                gender = 'female'

            visitors_by_gender[gender].append(participant)

        logger.info(f"👔 Facilitators/Organizers (single rooms): {len(facilitators)}")
        logger.info(f"👥 Visitors by gender: male={len(visitors_by_gender['male'])}, female={len(visitors_by_gender['female'])}, other={len(visitors_by_gender['other'])}")
        
        # Assign rooms based on new configuration
        rooms_used = {"single": 0, "double": 0}

        # STEP 1: Assign facilitators/organizers to single rooms first
        logger.info(f"🏠 Step 1: Assigning {len(facilitators)} facilitators/organizers to single rooms")
        for facilitator in facilitators:
            if rooms_used["single"] < vendor_setup.single_rooms:
                success = _create_room_allocation(
                    db, facilitator, event, vendor_setup, "single", 1
                )
                if success:
                    rooms_used["single"] += 1
                    vendor_setup.current_occupants += 1
                    logger.info(f"🏠 Assigned single room to facilitator {facilitator.full_name}")
                else:
                    logger.error(f"❌ Failed to assign single room to facilitator {facilitator.full_name}")
            else:
                logger.warning(f"⚠️ No single rooms available for facilitator {facilitator.full_name}")

        # STEP 2: Pair same-gender visitors into double rooms
        logger.info(f"🏠 Step 2: Pairing visitors into double rooms")
        for gender in ["male", "female"]:
            visitors = visitors_by_gender[gender].copy()
            logger.info(f"🏠 Processing {len(visitors)} {gender} visitors")

            # Assign double rooms (2 people per room)
            while len(visitors) >= 2 and rooms_used["double"] < vendor_setup.double_rooms:
                visitor1 = visitors.pop(0)
                visitor2 = visitors.pop(0)

                # Create allocations for both visitors sharing a double room
                success1 = _create_room_allocation(
                    db, visitor1, event, vendor_setup, "double", 2,
                    roommate_name=visitor2.full_name
                )
                success2 = _create_room_allocation(
                    db, visitor2, event, vendor_setup, "double", 2,
                    roommate_name=visitor1.full_name
                )

                if success1 and success2:
                    rooms_used["double"] += 1
                    vendor_setup.current_occupants += 2
                    logger.info(f"🏠 Assigned double room to {visitor1.full_name} and {visitor2.full_name}")
                else:
                    logger.error(f"❌ Failed to assign double room to {visitor1.full_name} and {visitor2.full_name}")

            # Assign remaining unpaired visitors to single rooms
            for visitor in visitors:
                if rooms_used["single"] < vendor_setup.single_rooms:
                    success = _create_room_allocation(
                        db, visitor, event, vendor_setup, "single", 1
                    )
                    if success:
                        rooms_used["single"] += 1
                        vendor_setup.current_occupants += 1
                        logger.info(f"🏠 Assigned single room to unpaired visitor {visitor.full_name}")
                    else:
                        logger.error(f"❌ Failed to assign single room to {visitor.full_name}")
                else:
                    logger.warning(f"⚠️ No single rooms available for {visitor.full_name}")

        # STEP 3: Assign "other" gender visitors to single rooms
        logger.info(f"🏠 Step 3: Assigning {len(visitors_by_gender['other'])} other-gender visitors to single rooms")
        for visitor in visitors_by_gender["other"]:
            if rooms_used["single"] < vendor_setup.single_rooms:
                success = _create_room_allocation(
                    db, visitor, event, vendor_setup, "single", 1
                )
                if success:
                    rooms_used["single"] += 1
                    vendor_setup.current_occupants += 1
                    logger.info(f"🏠 Assigned single room to {visitor.full_name}")
                else:
                    logger.error(f"❌ Failed to assign single room to {visitor.full_name}")
            else:
                logger.warning(f"⚠️ No single rooms available for {visitor.full_name}")
        
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

        # Get board type from event and rate from vendor
        board_type = event.accommodation_type  # e.g., 'FullBoard', 'HalfBoard'
        rate_per_day = None
        rate_currency = 'KES'

        # Get vendor rates
        if vendor_setup.vendor_accommodation_id:
            vendor_rate_query = db.execute(text("""
                SELECT rate_bed_breakfast, rate_half_board, rate_full_board, rate_bed_only, rate_currency
                FROM vendor_accommodations WHERE id = :vendor_id
            """), {"vendor_id": vendor_setup.vendor_accommodation_id}).fetchone()

            if vendor_rate_query:
                rate_currency = vendor_rate_query.rate_currency or 'KES'
                if board_type == 'FullBoard':
                    rate_per_day = vendor_rate_query.rate_full_board
                elif board_type == 'HalfBoard':
                    rate_per_day = vendor_rate_query.rate_half_board
                elif board_type == 'BedAndBreakfast':
                    rate_per_day = vendor_rate_query.rate_bed_breakfast
                elif board_type == 'BedOnly':
                    rate_per_day = vendor_rate_query.rate_bed_only

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
            notes=notes,
            board_type=board_type,
            rate_per_day=rate_per_day,
            rate_currency=rate_currency
        )

        db.add(allocation)
        return True

    except Exception as e:
        logger.error(f"💥 Error creating room allocation for {participant.full_name}: {str(e)}")
        return False
