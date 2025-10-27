from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.core.permissions import has_transport_permissions
from pydantic import BaseModel
from typing import Optional
import requests
import hmac
import hashlib
import base64
import time
import secrets
import json
from datetime import datetime, timedelta

router = APIRouter()

class AbsoluteCabsBookingRequest(BaseModel):
    pickup_address: str
    pickup_latitude: float
    pickup_longitude: float
    dropoff_address: str
    dropoff_latitude: float
    dropoff_longitude: float
    pickup_time: str
    passenger_name: str
    passenger_phone: str
    passenger_email: str
    vehicle_type: str = "SUV"
    flight_details: Optional[str] = ""
    notes: Optional[str] = ""

class AbsoluteCabsAPI:
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

    def _ensure_authenticated(self):
        if not self.access_token or datetime.now() >= self.token_expires_at:
            self.get_access_token()

    def _generate_signature(self, method, path, body, timestamp, nonce):
        if body:
            body_hash = hashlib.sha256(json.dumps(body).encode()).hexdigest()
        else:
            body_hash = hashlib.sha256(b'').hexdigest()
        
        canonical_string = f"{method}\n{path}\n{timestamp}\n{body_hash}\n{nonce}"
        
        signature = hmac.new(
            self.hmac_secret.encode(),
            canonical_string.encode(),
            hashlib.sha256
        ).digest()
        
        return base64.b64encode(signature).decode()

    def create_booking(self, booking_data: dict):
        self._ensure_authenticated()
        
        timestamp = str(int(time.time()))
        nonce = secrets.token_hex(16)
        signature = self._generate_signature("POST", "/api/bookings", booking_data, timestamp, nonce)
        
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "X-Client-Id": self.client_id,
            "X-Timestamp": timestamp,
            "X-Nonce": nonce,
            "X-Signature": signature,
            "Content-Type": "application/json"
        }
        
        url = f"{self.base_url}/api/bookings"
        response = requests.post(url, json=booking_data, headers=headers)
        response.raise_for_status()
        
        return response.json()

@router.post("/create-absolute-booking")
def create_absolute_cabs_booking(
    booking_request: AbsoluteCabsBookingRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a booking with Absolute Cabs API"""
    if not has_transport_permissions(current_user, db):
        raise HTTPException(status_code=403, detail="Not authorized")
    
    try:
        # Prepare booking data for Absolute Cabs API
        booking_data = {
            "pickup_address": booking_request.pickup_address,
            "pickup_latitude": booking_request.pickup_latitude,
            "pickup_longitude": booking_request.pickup_longitude,
            "dropoff_address": booking_request.dropoff_address,
            "dropoff_latitude": booking_request.dropoff_latitude,
            "dropoff_longitude": booking_request.dropoff_longitude,
            "pickup_time": booking_request.pickup_time,
            "passenger_name": booking_request.passenger_name,
            "passenger_phone": booking_request.passenger_phone,
            "passenger_email": booking_request.passenger_email,
            "vehicle_type": booking_request.vehicle_type,
            "flightdetails": booking_request.flight_details,
            "notes": booking_request.notes
        }
        
        # Create booking with Absolute Cabs
        absolute_api = AbsoluteCabsAPI()
        api_response = absolute_api.create_booking(booking_data)
        
        # Extract booking reference from response
        booking_reference = None
        if "booking" in api_response and "ref_no" in api_response["booking"]:
            booking_reference = api_response["booking"]["ref_no"]
        
        return {
            "success": True,
            "message": "Booking created successfully with Absolute Cabs",
            "booking_reference": booking_reference,
            "api_response": api_response
        }
        
    except requests.exceptions.RequestException as e:
        raise HTTPException(
            status_code=500, 
            detail=f"Failed to create booking with Absolute Cabs: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"Error creating booking: {str(e)}"
        )

@router.get("/test-absolute-connection")
def test_absolute_cabs_connection(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Test connection to Absolute Cabs API"""
    if not has_transport_permissions(current_user, db):
        raise HTTPException(status_code=403, detail="Not authorized")
    
    try:
        absolute_api = AbsoluteCabsAPI()
        absolute_api.get_access_token()
        
        return {
            "success": True,
            "message": "Successfully connected to Absolute Cabs API",
            "token_expires_at": absolute_api.token_expires_at.isoformat() if absolute_api.token_expires_at else None
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to connect to Absolute Cabs API: {str(e)}"
        )