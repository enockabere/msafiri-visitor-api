"""
Absolute Cabs API Integration Service
Handles authentication, booking creation, and vehicle type management
"""

import requests
import hmac
import hashlib
import base64
import time
import secrets
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from sqlalchemy.orm import Session
from app.models.transport_provider import TransportProvider
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)

class AbsoluteCabsService:
    def __init__(self, provider_config: TransportProvider):
        self.client_id = provider_config.client_id
        self.client_secret = provider_config.client_secret
        self.hmac_secret = provider_config.hmac_secret
        self.base_url = provider_config.api_base_url.rstrip('/')
        self.token_url = provider_config.token_url
        self.access_token = None
        self.token_expires_at = None

    def get_access_token(self) -> str:
        """Obtain OAuth2 access token"""
        payload = {
            "grant_type": "client_credentials",
            "client_id": self.client_id,
            "client_secret": self.client_secret
        }
        
        try:
            response = requests.post(
                self.token_url,
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=30
            )
            response.raise_for_status()
            
            data = response.json()
            self.access_token = data.get('access_token')
            expires_in = data.get('expires_in', 3600)
            self.token_expires_at = datetime.now() + timedelta(seconds=expires_in - 60)
            
            logger.info("Successfully obtained Absolute Cabs access token")
            return self.access_token
            
        except Exception as e:
            logger.error(f"Failed to obtain access token: {str(e)}")
            raise

    def _ensure_valid_token(self):
        """Ensure we have a valid access token"""
        if not self.access_token or not self.token_expires_at:
            self.get_access_token()
        elif datetime.now() >= self.token_expires_at:
            logger.info("Token expired, refreshing...")
            self.get_access_token()

    def _generate_signature(self, method: str, path: str, timestamp: int, body: str, nonce: str) -> str:
        """Generate HMAC-SHA256 signature"""
        body_hash = hashlib.sha256(body.encode('utf-8')).hexdigest()
        canonical_string = f"{method}\n{path}\n{timestamp}\n{body_hash}\n{nonce}"
        
        signature = hmac.new(
            self.hmac_secret.encode('utf-8'),
            canonical_string.encode('utf-8'),
            hashlib.sha256
        ).digest()
        
        return base64.b64encode(signature).decode('utf-8')

    def _make_request(self, method: str, endpoint: str, data: Optional[Dict] = None) -> Dict:
        """Make authenticated and signed API request"""
        self._ensure_valid_token()
        
        url = f"{self.base_url}{endpoint}"
        path = endpoint
        timestamp = int(time.time())
        nonce = secrets.token_hex(16)
        body = json.dumps(data) if data else ""
        
        signature = self._generate_signature(method, path, timestamp, body, nonce)
        
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "X-Client-Id": self.client_id,
            "X-Timestamp": str(timestamp),
            "X-Nonce": nonce,
            "X-Signature": signature,
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        
        try:
            if method == "GET":
                response = requests.get(url, headers=headers, timeout=30)
            elif method == "POST":
                response = requests.post(url, headers=headers, json=data, timeout=30)
            else:
                raise ValueError(f"Unsupported method: {method}")
            
            response.raise_for_status()
            return response.json()
            
        except requests.exceptions.HTTPError as e:
            # Log detailed error response for debugging
            error_details = "Unknown error"
            try:
                error_response = response.json()
                error_details = json.dumps(error_response, indent=2)
                logger.error(f"API request failed: {method} {endpoint} - Status: {response.status_code}")
                logger.error(f"Error response body: {error_details}")
            except:
                error_details = response.text
                logger.error(f"API request failed: {method} {endpoint} - Status: {response.status_code}")
                logger.error(f"Error response text: {error_details}")
            raise Exception(f"API Error {response.status_code}: {error_details}")
        except Exception as e:
            logger.error(f"API request failed: {method} {endpoint} - {str(e)}")
            raise

    def get_vehicle_types(self) -> List[Dict]:
        """Fetch available vehicle types"""
        try:
            response = self._make_request("GET", "/api/vehicle-types")
            return response.get("data", [])
        except Exception as e:
            logger.error(f"Failed to fetch vehicle types: {str(e)}")
            raise

    def create_booking(self, booking_data: Dict) -> Dict:
        """Create a new booking"""
        try:
            # Print the payload being sent
            logger.info(f"🚗 ABSOLUTE CABS BOOKING PAYLOAD: {json.dumps(booking_data, indent=2)}")
            print(f"🚗 ABSOLUTE CABS BOOKING PAYLOAD: {json.dumps(booking_data, indent=2)}")
            
            response = self._make_request("POST", "/api/bookings", booking_data)
            logger.info(f"Successfully created booking: {response}")
            return response
        except Exception as e:
            logger.error(f"Failed to create booking: {str(e)}")
            raise

    def get_bookings(self) -> Dict:
        """Fetch all bookings"""
        try:
            return self._make_request("GET", "/api/bookings")
        except Exception as e:
            logger.error(f"Failed to fetch bookings: {str(e)}")
            raise

    def get_booking(self, ref_no: str) -> Dict:
        """Fetch a single booking by reference number"""
        try:
            return self._make_request("GET", f"/api/bookings/{ref_no}")
        except Exception as e:
            logger.error(f"Failed to fetch booking {ref_no}: {str(e)}")
            raise
    
    def get_booking_details(self, ref_no: str) -> Dict:
        """Fetch detailed booking information by reference number"""
        try:
            response = self._make_request("GET", f"/api/bookings/{ref_no}")
            
            # Extract booking data from response
            if 'booking' in response:
                booking = response['booking']
            elif 'data' in response:
                booking = response['data']
            else:
                booking = response
            
            # Format the response for frontend consumption
            return {
                "success": True,
                "booking": {
                    "ref_no": booking.get("ref_no"),
                    "id": booking.get("id"),
                    "pickup_date": booking.get("pickup_date"),
                    "pickup_time": booking.get("pickup_time"),
                    "vehicle_type": booking.get("vehicle_type"),
                    "status": booking.get("status", "Pending"),
                    "pickup_address": booking.get("pickup_address"),
                    "pickup_latitude": booking.get("pickup_latitude"),
                    "pickup_longitude": booking.get("pickup_longitude"),
                    "dropoff_address": booking.get("dropoff_address"),
                    "dropoff_latitude": booking.get("dropoff_latitude"),
                    "dropoff_longitude": booking.get("dropoff_longitude"),
                    "flightdetails": booking.get("flightdetails"),
                    "notes": booking.get("notes"),
                    "passengers": booking.get("passengers", []),
                    "drivers": booking.get("drivers", []),
                    "vehicles": booking.get("vehicles", []),
                    "waypoints": booking.get("waypoints", [])
                }
            }
        except Exception as e:
            logger.error(f"Failed to fetch booking details {ref_no}: {str(e)}")
            raise

def get_absolute_cabs_service(tenant_id: int, db: Session) -> Optional[AbsoluteCabsService]:
    """Get configured Absolute Cabs service for a tenant"""
    provider = db.query(TransportProvider).filter(
        TransportProvider.tenant_id == tenant_id,
        TransportProvider.provider_name == "absolute_cabs",
        TransportProvider.is_enabled == True
    ).first()
    
    if not provider:
        return None
    
    if not all([provider.client_id, provider.client_secret, provider.hmac_secret]):
        logger.error(f"Incomplete Absolute Cabs configuration for tenant {tenant_id}")
        return None
    
    return AbsoluteCabsService(provider)