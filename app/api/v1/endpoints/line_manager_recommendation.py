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

@router.get("/participant/{participant_id}")
async def get_recommendation_by_participant(
    participant_id: int,
    db: Session = Depends(get_db)
):
    """Get line manager recommendation by participant ID"""
    
    print(f"=== DEBUG: Fetching recommendation for participant ID: {participant_id} ===")
    
    # First check if any recommendations exist at all
    all_recs = db.execute(
        text("SELECT id, registration_id, line_manager_email, submitted_at FROM line_manager_recommendations ORDER BY created_at DESC")
    ).fetchall()
    
    print(f"DEBUG: Total recommendations in database: {len(all_recs)}")
    for rec in all_recs:
        print(f"DEBUG: Rec ID {rec[0]}, Registration ID: {rec[1]}, Manager: {rec[2]}, Submitted: {rec[3]}")
    
    result = db.execute(
        text("""
            SELECT id, line_manager_email, recommendation_text, submitted_at, created_at
            FROM line_manager_recommendations 
            WHERE registration_id = :participant_id
            ORDER BY created_at DESC
            LIMIT 1
        """),
        {"participant_id": participant_id}
    ).fetchone()
    
    print(f"DEBUG: Query result for participant {participant_id}: {result}")
    
    if not result:
        print(f"DEBUG: No recommendation found for participant {participant_id}")
        raise HTTPException(status_code=404, detail="No recommendation found for this participant")
    
    print(f"DEBUG: Returning recommendation data: {result}")
    return {
        "id": result[0],
        "line_manager_email": result[1],
        "recommendation_text": result[2],
        "submitted_at": result[3],
        "created_at": result[4]
    }