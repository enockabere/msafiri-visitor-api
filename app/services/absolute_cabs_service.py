import requests
import hmac
import hashlib
import base64
import time
import secrets
import json
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from app.crud.transport_provider import transport_provider

class AbsoluteCabsService:
    def __init__(self, db: Session, tenant_id: int):
        self.db = db
        self.tenant_id = tenant_id
        self.provider_config = None
        self.access_token = None
        self.token_expires_at = None
        self._load_config()
    
    def _load_config(self):
        """Load provider configuration from database"""
        self.provider_config = transport_provider.get_by_tenant_and_provider(
            self.db, tenant_id=self.tenant_id, provider_name="absolute_cabs"
        )
        if not self.provider_config or not self.provider_config.is_enabled:
            raise ValueError("Absolute Cabs not configured or disabled for this tenant")
    
    def get_access_token(self) -> bool:
        """Get OAuth2 access token"""
        if not self.provider_config:
            return False
            
        payload = {
            "grant_type": "client_credentials",
            "client_id": self.provider_config.client_id,
            "client_secret": self.provider_config.client_secret,
            "scope": "*"
        }
        
        response = requests.post(self.provider_config.token_url, json=payload)
        response.raise_for_status()
        
        data = response.json()
        self.access_token = data['access_token']
        expires_in = data.get('expires_in', 3600)
        self.token_expires_at = datetime.now() + timedelta(seconds=expires_in - 60)
        
        return True
    
    def _ensure_authenticated(self):
        """Ensure we have a valid token"""
        if not self.access_token or datetime.now() >= self.token_expires_at:
            self.get_access_token()
    
    def _generate_signature(self, method: str, path: str, body: Optional[Dict], timestamp: str, nonce: str) -> str:
        """Generate HMAC-SHA256 signature"""
        if body:
            body_hash = hashlib.sha256(json.dumps(body).encode()).hexdigest()
        else:
            body_hash = hashlib.sha256(b'').hexdigest()
        
        canonical_string = f"{method}\n{path}\n{timestamp}\n{body_hash}\n{nonce}"
        
        signature = hmac.new(
            self.provider_config.hmac_secret.encode(),
            canonical_string.encode(),
            hashlib.sha256
        ).digest()
        
        return base64.b64encode(signature).decode()
    
    def create_booking(self, booking_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a cab booking"""
        self._ensure_authenticated()
        
        timestamp = str(int(time.time()))
        nonce = secrets.token_hex(16)
        signature = self._generate_signature("POST", "/api/bookings", booking_data, timestamp, nonce)
        
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "X-Client-Id": self.provider_config.client_id,
            "X-Timestamp": timestamp,
            "X-Nonce": nonce,
            "X-Signature": signature,
            "Content-Type": "application/json"
        }
        
        url = f"{self.provider_config.api_base_url}/api/bookings"
        response = requests.post(url, json=booking_data, headers=headers)
        response.raise_for_status()
        
        return response.json()
    
    def get_bookings(self) -> Dict[str, Any]:
        """Get all bookings"""
        self._ensure_authenticated()
        
        timestamp = str(int(time.time()))
        nonce = secrets.token_hex(16)
        signature = self._generate_signature("GET", "/api/bookings", None, timestamp, nonce)
        
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "X-Client-Id": self.provider_config.client_id,
            "X-Timestamp": timestamp,
            "X-Nonce": nonce,
            "X-Signature": signature
        }
        
        url = f"{self.provider_config.api_base_url}/api/bookings"
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        
        return response.json()