from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.models.event_participant import EventParticipant

router = APIRouter()

@router.get("/poa/{poa_slug}")
def get_public_poa(poa_slug: str, db: Session = Depends(get_db)):
    """Public endpoint to access POA documents via QR code"""
    
    # The slug is generated from participant_id and event_id
    # We need to find participants with POA URLs and check if the slug matches
    participants = db.query(EventParticipant).filter(
        EventParticipant.proof_of_accommodation_url.isnot(None)
    ).all()
    
    # Generate slug for each participant and check for match
    for participant in participants:
        if participant.proof_of_accommodation_url:
            # Generate the same slug that would be created for this participant
            from app.services.proof_of_accommodation import generate_poa_slug
            expected_slug = generate_poa_slug(participant.id, participant.event_id)
            
            if expected_slug == poa_slug:
                # Found matching participant, redirect to their POA document
                if participant.proof_of_accommodation_url.startswith("http"):
                    return RedirectResponse(url=participant.proof_of_accommodation_url)
    
    # No matching POA found
    raise HTTPException(status_code=404, detail="POA document not found")