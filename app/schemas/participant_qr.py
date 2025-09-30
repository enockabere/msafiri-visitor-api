from pydantic import BaseModel
from typing import List, Dict, Any
from datetime import datetime

class AllocationItem(BaseModel):
    item_name: str
    item_type: str
    allocated_quantity: int
    redeemed_quantity: int
    remaining_quantity: int

class QRAllocationData(BaseModel):
    participant_id: int
    participant_name: str
    participant_email: str
    event_id: int
    event_title: str
    event_location: str
    event_start_date: str = None
    event_end_date: str = None
    total_drinks: int
    remaining_drinks: int
    redeemed_drinks: int = 0

class ParticipantQRResponse(BaseModel):
    qr_token: str
    qr_data_url: str  # Base64 encoded QR code image
    allocation_summary: QRAllocationData