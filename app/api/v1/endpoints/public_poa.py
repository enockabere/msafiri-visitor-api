from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.db.database import get_db
from app.models.event_participant import EventParticipant

router = APIRouter()

@router.get("/poa/events/{event_id}/participant/{participant_id}")
def get_poa_direct(event_id: int, participant_id: int, db: Session = Depends(get_db)):
    """Direct endpoint to access POA documents via QR code (like LOI)"""
    
    # Find participant
    query = text("""
        SELECT proof_of_accommodation_url
        FROM event_participants
        WHERE id = :participant_id AND event_id = :event_id
    """)
    
    result = db.execute(query, {
        "participant_id": participant_id,
        "event_id": event_id
    }).fetchone()
    
    if result and result.proof_of_accommodation_url:
        # Redirect to the POA document
        if result.proof_of_accommodation_url.startswith("http"):
            return RedirectResponse(url=result.proof_of_accommodation_url)
    
    # No matching POA found
    raise HTTPException(status_code=404, detail="POA document not found")

@router.get("/poa/{poa_slug}")
def get_public_poa(poa_slug: str, db: Session = Depends(get_db)):
    """Public endpoint to access POA documents via QR code (slug-based, legacy)"""
    
    # Find participant by poa_slug
    participant = db.query(EventParticipant).filter(
        EventParticipant.poa_slug == poa_slug
    ).first()
    
    if participant and participant.proof_of_accommodation_url:
        # Redirect to the POA document
        if participant.proof_of_accommodation_url.startswith("http"):
            return RedirectResponse(url=participant.proof_of_accommodation_url)
    
    # No matching POA found
    raise HTTPException(status_code=404, detail="POA document not found")