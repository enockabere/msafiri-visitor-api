from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.models.passport_record import PassportRecord
from app.models.event_participant import EventParticipant
import requests
import os

router = APIRouter()

@router.get("/participant/{participant_email}/event/{event_id}/loi")
async def get_participant_loi(
    participant_email: str,
    event_id: int,
    db: Session = Depends(get_db)
):
    """Get LOI data for a participant by email and event ID"""
    
    # First, verify the participant exists for this event
    participant = db.query(EventParticipant).filter(
        EventParticipant.email == participant_email,
        EventParticipant.event_id == event_id
    ).first()
    
    if not participant:
        raise HTTPException(
            status_code=404,
            detail="Participant not found for this event"
        )
    
    # Get the passport record (which contains the record_id for LOI)
    passport_record = db.query(PassportRecord).filter(
        PassportRecord.user_email == participant_email,
        PassportRecord.event_id == event_id
    ).first()
    
    if not passport_record:
        raise HTTPException(
            status_code=404,
            detail="No LOI record found for this participant"
        )
    
    # Fetch LOI data from external API using the record_id
    try:
        API_URL = f"{os.getenv('PASSPORT_API_URL', 'https://ko-hr.kenya.msf.org/api/v1')}/get-passport-data/{passport_record.record_id}"
        API_KEY = os.getenv('PASSPORT_API_KEY', 'n5BOC1ZH*o64Ux^%!etd4$rfUoj7iQrXSXOgk6uW')
        
        headers = {
            'x-api-key': API_KEY,
            'Content-Type': 'application/json',
            'Accept': 'application/json',
        }
        
        payload = {"passport_id": passport_record.record_id}
        response = requests.get(API_URL, json=payload, headers=headers, timeout=30)
        
        if response.status_code == 200:
            response_data = response.json()
            # Extract data from JSON-RPC response structure
            if response_data.get('result', {}).get('status') == 'success':
                loi_data = response_data['result']['data']
                return {
                    "participant_email": participant_email,
                    "participant_name": participant.full_name,
                    "event_id": event_id,
                    "record_id": passport_record.record_id,
                    "loi_data": loi_data
                }
            else:
                raise HTTPException(
                    status_code=400,
                    detail="Failed to fetch LOI data from external API"
                )
        else:
            raise HTTPException(
                status_code=response.status_code,
                detail=f"Failed to fetch LOI data from external API: {response.text}"
            )
            
    except requests.RequestException as e:
        raise HTTPException(
            status_code=500,
            detail=f"External API error: {str(e)}"
        )

@router.get("/record/{record_id}/loi")
async def get_loi_by_record_id(record_id: int):
    """Get LOI data directly by record ID (for public access)"""
    
    try:
        API_URL = f"{os.getenv('PASSPORT_API_URL', 'https://ko-hr.kenya.msf.org/api/v1')}/get-passport-data/{record_id}"
        API_KEY = os.getenv('PASSPORT_API_KEY', 'n5BOC1ZH*o64Ux^%!etd4$rfUoj7iQrXSXOgk6uW')
        
        headers = {
            'x-api-key': API_KEY,
            'Content-Type': 'application/json',
            'Accept': 'application/json',
        }
        
        payload = {"passport_id": record_id}
        response = requests.get(API_URL, json=payload, headers=headers, timeout=30)
        
        if response.status_code == 200:
            response_data = response.json()
            # Extract data from JSON-RPC response structure
            if response_data.get('result', {}).get('status') == 'success':
                return response_data['result']['data']
            else:
                raise HTTPException(
                    status_code=400,
                    detail="Failed to fetch LOI data from external API"
                )
        else:
            raise HTTPException(
                status_code=response.status_code,
                detail=f"Failed to fetch LOI data: {response.text}"
            )
            
    except requests.RequestException as e:
        raise HTTPException(
            status_code=500,
            detail=f"External API error: {str(e)}"
        )