from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.database import get_db
from pydantic import BaseModel
from typing import Optional
from sqlalchemy import text
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

class RecommendationSubmission(BaseModel):
    recommendation_text: str

@router.get("/line-manager-recommendation/{token}")
async def get_recommendation_details(
    token: str,
    db: Session = Depends(get_db)
):
    """Get recommendation request details by token"""
    
    result = db.execute(
        text("""
            SELECT r.id, r.participant_name, r.participant_email, r.operation_center,
                   r.event_title, r.event_dates, r.event_location, r.recommendation_text,
                   r.submitted_at, e.registration_deadline
            FROM line_manager_recommendations r
            JOIN events e ON r.event_id = e.id
            WHERE r.recommendation_token = :token
        """),
        {"token": token}
    ).fetchone()
    
    if not result:
        raise HTTPException(status_code=404, detail="Recommendation request not found")
    
    return {
        "id": result[0],
        "participant_name": result[1],
        "participant_email": result[2],
        "operation_center": result[3],
        "event_title": result[4],
        "event_dates": result[5],
        "event_location": result[6],
        "recommendation_text": result[7],
        "submitted_at": result[8],
        "registration_deadline": result[9],
        "already_submitted": result[8] is not None
    }

@router.post("/line-manager-recommendation/{token}")
async def submit_recommendation(
    token: str,
    submission: RecommendationSubmission,
    db: Session = Depends(get_db)
):
    """Submit line manager recommendation"""
    
    # Check if recommendation exists and not already submitted
    result = db.execute(
        text("""
            SELECT id, submitted_at FROM line_manager_recommendations 
            WHERE recommendation_token = :token
        """),
        {"token": token}
    ).fetchone()
    
    if not result:
        raise HTTPException(status_code=404, detail="Recommendation request not found")
    
    if result[1] is not None:
        raise HTTPException(status_code=400, detail="Recommendation already submitted")
    
    # Update recommendation
    db.execute(
        text("""
            UPDATE line_manager_recommendations 
            SET recommendation_text = :text, submitted_at = CURRENT_TIMESTAMP
            WHERE recommendation_token = :token
        """),
        {"text": submission.recommendation_text, "token": token}
    )
    
    db.commit()
    
    logger.info(f"✅ Recommendation submitted for token {token}")
    
    return {"message": "Recommendation submitted successfully"}

@router.get("/debug/all")
async def debug_all_recommendations(db: Session = Depends(get_db)):
    """DEBUG: Print all recommendations in database"""
    
    print("=== DEBUG: ALL RECOMMENDATIONS IN DATABASE ===")
    
    all_recs = db.execute(
        text("""
            SELECT id, registration_id, participant_name, participant_email, 
                   line_manager_email, recommendation_text, submitted_at, created_at,
                   recommendation_token, event_id
            FROM line_manager_recommendations 
            ORDER BY created_at DESC
        """)
    ).fetchall()
    
    print(f"DEBUG: Total recommendations: {len(all_recs)}")
    
    for i, rec in enumerate(all_recs, 1):
        print(f"\nDEBUG: Recommendation #{i}:")
        print(f"  ID: {rec[0]}")
        print(f"  Registration ID: {rec[1]}")
        print(f"  Participant Name: {rec[2]}")
        print(f"  Participant Email: {rec[3]}")
        print(f"  Line Manager Email: {rec[4]}")
        print(f"  Recommendation Text: {rec[5][:100] if rec[5] else 'None'}...")
        print(f"  Submitted At: {rec[6]}")
        print(f"  Created At: {rec[7]}")
        print(f"  Token: {rec[8][:10] if rec[8] else 'None'}...")
        print(f"  Event ID: {rec[9]}")
    
    return {"total_recommendations": len(all_recs), "data": "Check server logs"}

@router.get("/debug/create-test/{participant_id}")
async def create_test_recommendation(
    participant_id: int,
    db: Session = Depends(get_db)
):
    """DEBUG: Create test recommendation for participant"""
    
    print(f"=== DEBUG: Creating test recommendation for participant {participant_id} ===")
    
    # Insert test recommendation
    db.execute(
        text("""
            INSERT INTO line_manager_recommendations 
            (registration_id, participant_name, participant_email, line_manager_email, 
             recommendation_text, submitted_at, created_at, recommendation_token, event_id)
            VALUES (:registration_id, 'Test Participant', 'test@example.com', 'manager@test.com',
                    'This is a test recommendation for debugging purposes.', 
                    CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, 'test-token-123', 41)
        """),
        {"registration_id": participant_id}
    )
    
    db.commit()
    print(f"DEBUG: Test recommendation created for participant {participant_id}")
    
    return {"message": f"Test recommendation created for participant {participant_id}"}

@router.get("/participant/{participant_id}")
async def get_recommendation_by_participant(
    participant_id: int,
    event_id: int = 41,  # Default to current event
    db: Session = Depends(get_db)
):
    """Get line manager recommendation by participant ID and event ID"""
    
    print(f"=== DEBUG: Fetching recommendation for participant ID: {participant_id}, event ID: {event_id} ===")
    
    # First check if any recommendations exist at all
    all_recs = db.execute(
        text("SELECT id, registration_id, event_id, participant_email, line_manager_email, submitted_at FROM line_manager_recommendations ORDER BY created_at DESC")
    ).fetchall()
    
    print(f"DEBUG: Total recommendations in database: {len(all_recs)}")
    for rec in all_recs:
        print(f"DEBUG: Rec ID {rec[0]}, Registration ID: {rec[1]}, Event ID: {rec[2]}, Email: {rec[3]}, Manager: {rec[4]}, Submitted: {rec[5]}")
    
    # Try to find by registration_id and event_id first
    result = db.execute(
        text("""
            SELECT id, line_manager_email, recommendation_text, submitted_at, created_at
            FROM line_manager_recommendations 
            WHERE registration_id = :participant_id AND event_id = :event_id
            ORDER BY created_at DESC
            LIMIT 1
        """),
        {"participant_id": participant_id, "event_id": event_id}
    ).fetchone()
    
    print(f"DEBUG: Query result for participant {participant_id}, event {event_id}: {result}")
    
    # If not found, try by participant email match
    if not result:
        print(f"DEBUG: No direct match, trying email match...")
        
        # Get participant email from public_registrations
        participant_email = db.execute(
            text("SELECT personal_email FROM public_registrations WHERE id = :participant_id"),
            {"participant_id": participant_id}
        ).fetchone()
        
        if participant_email:
            email = participant_email[0]
            print(f"DEBUG: Found participant email: {email}")
            
            result = db.execute(
                text("""
                    SELECT id, line_manager_email, recommendation_text, submitted_at, created_at
                    FROM line_manager_recommendations 
                    WHERE participant_email = :email AND event_id = :event_id
                    ORDER BY created_at DESC
                    LIMIT 1
                """),
                {"email": email, "event_id": event_id}
            ).fetchone()
            
            print(f"DEBUG: Email match result: {result}")
    
    if not result:
        print(f"DEBUG: No recommendation found for participant {participant_id} in event {event_id}")
        raise HTTPException(status_code=404, detail="No recommendation found for this participant")
    
    print(f"DEBUG: Returning recommendation data: {result}")
    return {
        "id": result[0],
        "line_manager_email": result[1],
        "recommendation_text": result[2],
        "submitted_at": result[3],
        "created_at": result[4]
    }