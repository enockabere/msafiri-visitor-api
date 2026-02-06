from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List, Dict, Any
from datetime import datetime, timedelta
from app.db.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.core.permissions import has_transport_permissions
from app.models.event_participant import EventParticipant
from app.models.accommodation import RoomAssignment
from app.models.transport_booking import TransportBooking, BookingType, BookingStatus, VendorType

from app.schemas.transport_booking import TransportBookingCreate
from app.crud.transport_booking import transport_booking
import requests
import json

router = APIRouter()

class AbsoluteCabsIntegration:
    def __init__(self):
        self.client_id = "f5741192-e755-41d5-934a-80b279e08347"
        self.client_secret = "hFPWDy6CgZQdofBTm5DoBYcNa2d1coHTYWpjF0wp"
        self.hmac_secret = "3c478d99c0ddb35bd35d4dd13899c57e3c77cccbf2bf7244f5c3c60b9f557809"
        self.token_url = "https://api.absolutecabs.co.ke/oauth/token"
        self.base_url = "https://api.absolutecabs.co.ke"
        self.access_token = None
        self.token_expires_at = None

    def get_access_token(self):
        payload = {
            "grant_type": "client_credentials",
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "scope": "*"
        }
        response = requests.post(self.token_url, json=payload)
        response.raise_for_status()
        data = response.json()
        self.access_token = data['access_token']
        expires_in = data.get('expires_in', 3600)
        self.token_expires_at = datetime.now() + timedelta(seconds=expires_in - 60)
        return True

    def create_booking(self, booking_data: dict):
        if not self.access_token or datetime.now() >= self.token_expires_at:
            self.get_access_token()
        
        import hmac
        import hashlib
        import base64
        import time
        import secrets
        
        timestamp = str(int(time.time()))
        nonce = secrets.token_hex(16)
        
        body_hash = hashlib.sha256(json.dumps(booking_data).encode()).hexdigest()
        canonical_string = f"POST\n/api/bookings\n{timestamp}\n{body_hash}\n{nonce}"
        signature = hmac.new(
            self.hmac_secret.encode(),
            canonical_string.encode(),
            hashlib.sha256
        ).digest()
        signature_b64 = base64.b64encode(signature).decode()
        
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "X-Client-Id": self.client_id,
            "X-Timestamp": timestamp,
            "X-Nonce": nonce,
            "X-Signature": signature_b64,
            "Content-Type": "application/json"
        }
        
        url = f"{self.base_url}/api/bookings"
        response = requests.post(url, json=booking_data, headers=headers)
        response.raise_for_status()
        return response.json()

@router.post("/auto-create-bookings")
def auto_create_transport_bookings(
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Automatically create transport bookings for international visitors"""
    if not has_transport_permissions(current_user, db):
        raise HTTPException(status_code=403, detail="Not authorized")
    
    # Get upcoming events (next 30 days)
    from app.models.event import Event
    upcoming_events = db.query(Event).filter(
        Event.start_date >= datetime.now(),
        Event.start_date <= datetime.now() + timedelta(days=30)
    ).all()
    
    created_bookings = []
    
    for event in upcoming_events:
        # Get international participants who are confirmed/selected
        international_participants = db.query(EventParticipant).filter(
            EventParticipant.event_id == event.id,
            EventParticipant.status.in_(["selected", "registered"]),
            EventParticipant.travelling_from_country.isnot(None),
            EventParticipant.travelling_from_country != "Kenya"
        ).all()
        
        for participant in international_participants:
            # Check if transport booking already exists
            existing_booking = db.query(TransportBooking).filter(
                TransportBooking.participant_ids.contains([participant.id])
            ).first()
            
            if existing_booking:
                continue
                
            # Get participant's accommodations ordered by check-in date
            accommodations = db.query(RoomAssignment).filter(
                RoomAssignment.participant_id == participant.id
            ).order_by(RoomAssignment.check_in_date).all()
            
            if not accommodations:
                continue
                
            # Create airport pickup booking
            first_accommodation = accommodations[0]
            
            booking_data = TransportBookingCreate(
                booking_type=BookingType.AIRPORT_PICKUP,
                participant_ids=[participant.id],
                pickup_locations=["JKIA Airport"],
                destination=f"{first_accommodation.hotel_name}, {first_accommodation.address}",
                scheduled_time=first_accommodation.check_in_date - timedelta(hours=2),
                vendor_type=VendorType.ABSOLUTE_TAXI,
                vendor_name="Absolute Cabs",
                flight_number="TBD",  # To be updated by admin
                arrival_time=first_accommodation.check_in_date - timedelta(hours=3),
                special_instructions=f"Pickup for {participant.full_name} from {participant.travelling_from_country}. Flight details to be confirmed.",
                admin_notes="Auto-created booking - requires admin confirmation before sending to vendor"
            )
            
            # Create the booking in pending status
            booking = transport_booking.create_booking(db, booking_data, "system_auto")
            created_bookings.append({
                "booking_id": booking.id,
                "participant": participant.full_name,
                "event": event.title,
                "destination": booking.destination
            })
    
    return {
        "message": f"Created {len(created_bookings)} automatic transport bookings",
        "bookings": created_bookings
    }

@router.post("/confirm-booking/{booking_id}")
def confirm_and_send_booking(
    booking_id: int,
    flight_details: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Confirm booking and send to Absolute Cabs"""
    if not has_transport_permissions(current_user, db):
        raise HTTPException(status_code=403, detail="Not authorized")
    
    booking = transport_booking.get_booking(db, booking_id)
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    
    if booking.status != BookingStatus.PENDING:
        raise HTTPException(status_code=400, detail="Only pending bookings can be confirmed")
    
    # Update flight details
    booking.flight_number = flight_details.get("flight_number")
    booking.arrival_time = datetime.fromisoformat(flight_details.get("arrival_time"))
    
    # Get participant details
    participant = db.query(EventParticipant).filter(
        EventParticipant.id == booking.participant_ids[0]
    ).first()
    
    if not participant:
        raise HTTPException(status_code=404, detail="Participant not found")
    
    # Get participant phone from user profile or use default
    participant_phone = getattr(participant, 'phone', None) or "254700000000"
    
    # Prepare Absolute Cabs booking data
    absolute_booking_data = {
        "pickup_address": booking.pickup_locations[0],
        "pickup_latitude": -1.319167,  # JKIA coordinates
        "pickup_longitude": 36.927778,
        "dropoff_address": booking.destination,
        "dropoff_latitude": -1.286389,  # Nairobi center (to be updated with actual coordinates)
        "dropoff_longitude": 36.817223,
        "pickup_time": booking.scheduled_time.strftime("%Y-%m-%dT%H:%M:%S"),
        "passenger_name": participant.full_name,
        "passenger_phone": participant_phone,
        "passenger_email": participant.email,
        "vehicle_type": "SUV",
        "flightdetails": booking.flight_number,
        "notes": booking.special_instructions or ""
    }
    
    try:
        # Send to Absolute Cabs
        absolute_api = AbsoluteCabsIntegration()
        api_response = absolute_api.create_booking(absolute_booking_data)
        
        # Update booking with API response
        booking.external_booking_id = api_response.get("booking", {}).get("ref_no")
        booking.api_response = api_response
        booking.status = BookingStatus.CONFIRMED
        booking.confirmed_by = current_user.email
        booking.confirmed_at = datetime.now()
        
        # Update driver details from API response
        if "booking" in api_response:
            booking_info = api_response["booking"]
            booking.driver_name = booking_info.get("driver_name")
            booking.driver_phone = booking_info.get("driver_phone")
            booking.vehicle_details = booking_info.get("vehicle_type_name")
        
        db.commit()
        
        return {
            "message": "Booking confirmed and sent to Absolute Cabs",
            "booking_reference": booking.external_booking_id,
            "api_response": api_response
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to send booking to Absolute Cabs: {str(e)}")

@router.get("/pending-bookings")
def get_pending_auto_bookings(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get all pending auto-created bookings that need admin confirmation"""
    if not has_transport_permissions(current_user, db):
        raise HTTPException(status_code=403, detail="Not authorized")
    
    pending_bookings = db.query(TransportBooking).filter(
        TransportBooking.status == BookingStatus.PENDING,
        TransportBooking.created_by == "system_auto"
    ).all()
    
    result = []
    for booking in pending_bookings:
        # Get participant details
        participants = db.query(EventParticipant).filter(
            EventParticipant.id.in_(booking.participant_ids)
        ).all()
        
        result.append({
            "id": booking.id,
            "booking_type": booking.booking_type.value,
            "participants": [{"id": p.id, "name": p.full_name, "email": p.email, "country": p.travelling_from_country} for p in participants],
            "pickup_locations": booking.pickup_locations,
            "destination": booking.destination,
            "scheduled_time": booking.scheduled_time.isoformat(),
            "flight_number": booking.flight_number,
            "arrival_time": booking.arrival_time.isoformat() if booking.arrival_time else None,
            "special_instructions": booking.special_instructions,
            "created_at": booking.created_at.isoformat()
        })
    
    return result
