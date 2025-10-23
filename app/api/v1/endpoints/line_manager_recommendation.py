from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.database import get_db
from pydantic import BaseModel
from typing import Optional
from sqlalchemy import text
import logging
import time

logger = logging.getLogger(__name__)
router = APIRouter()

class RecommendationSubmission(BaseModel):
    recommendation_text: str

@router.get("/test")
async def test_endpoint():
    """Test endpoint to verify router is working"""
    return {"message": "Line manager recommendation router is working", "timestamp": time.time()}

@router.get("/{token}")
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

@router.post("/{token}")
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

@router.get("/debug/match-emails/{participant_id}")
async def debug_email_match(
    participant_id: int,
    db: Session = Depends(get_db)
):
    """DEBUG: Check email matching for participant"""
    
    print(f"=== DEBUG: Email matching for participant {participant_id} ===")
    
    # Get participant email from event_participants
    participant_info = db.execute(
        text("SELECT email, full_name FROM event_participants WHERE id = :id"),
        {"id": participant_id}
    ).fetchone()
    
    if participant_info:
        email = participant_info[0]
        name = participant_info[1]
        print(f"DEBUG: Participant {participant_id}: {name} ({email})")
        
        # Check if recommendation exists for this email
        rec_check = db.execute(
            text("SELECT id, recommendation_text, submitted_at FROM line_manager_recommendations WHERE participant_email = :email AND event_id = 41"),
            {"email": email}
        ).fetchone()
        
        if rec_check:
            print(f"DEBUG: Found recommendation: ID {rec_check[0]}, submitted {rec_check[2]}")
            return {"participant": f"{name} ({email})", "recommendation_found": True, "rec_id": rec_check[0]}
        else:
            print(f"DEBUG: No recommendation found for {email}")
            return {"participant": f"{name} ({email})", "recommendation_found": False}
    else:
        print(f"DEBUG: Participant {participant_id} not found")
        return {"error": f"Participant {participant_id} not found"}

@router.get("/debug/registrations")
async def debug_registrations(db: Session = Depends(get_db)):
    """DEBUG: Show all public registrations"""
    
    print("=== DEBUG: ALL PUBLIC REGISTRATIONS ===")
    
    registrations = db.execute(
        text("""
            SELECT id, event_id, first_name, last_name, personal_email, created_at
            FROM public_registrations 
            WHERE event_id = 41
            ORDER BY created_at DESC
        """)
    ).fetchall()
    
    print(f"DEBUG: Total registrations for event 41: {len(registrations)}")
    
    for i, reg in enumerate(registrations, 1):
        print(f"\nDEBUG: Registration #{i}:")
        print(f"  ID: {reg[0]}")
        print(f"  Event ID: {reg[1]}")
        print(f"  Name: {reg[2]} {reg[3]}")
        print(f"  Email: {reg[4]}")
        print(f"  Created: {reg[5]}")
    
    return {"total_registrations": len(registrations), "data": "Check server logs"}

@router.get("/debug/create-test-for-email/{participant_id}")
async def create_test_for_participant_email(
    participant_id: int,
    db: Session = Depends(get_db)
):
    """DEBUG: Create test recommendation for participant email"""
    
    print(f"=== DEBUG: Creating test recommendation for participant {participant_id} ===")
    
    # Get participant info
    participant_info = db.execute(
        text("SELECT email, full_name FROM event_participants WHERE id = :id"),
        {"id": participant_id}
    ).fetchone()
    
    if not participant_info:
        return {"error": f"Participant {participant_id} not found"}
    
    email = participant_info[0]
    name = participant_info[1]
    print(f"DEBUG: Creating recommendation for {name} ({email})")
    
    # Insert test recommendation
    db.execute(
        text("""
            INSERT INTO line_manager_recommendations 
            (registration_id, participant_name, participant_email, line_manager_email, 
             recommendation_text, submitted_at, created_at, recommendation_token, event_id)
            VALUES (1, :name, :email, 'test-manager@msf.org',
                    'This is a test recommendation created for debugging. The participant shows excellent potential.', 
                    CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, :token, 41)
        """),
        {
            "name": name,
            "email": email,
            "token": f"test-{participant_id}-{int(time.time())}"
        }
    )
    
    db.commit()
    print(f"DEBUG: Test recommendation created for {name} ({email})")
    
    return {"message": f"Test recommendation created for {name} ({email})"}

@router.get("/debug/create-test/{registration_id}")
async def create_test_recommendation(
    registration_id: int,
    db: Session = Depends(get_db)
):
    """DEBUG: Create test recommendation for registration"""
    
    print(f"=== DEBUG: Creating test recommendation for registration {registration_id} ===")
    
    # Check if registration exists
    reg_check = db.execute(
        text("SELECT id, personal_email, first_name, last_name FROM public_registrations WHERE id = :id"),
        {"id": registration_id}
    ).fetchone()
    
    if not reg_check:
        print(f"DEBUG: Registration {registration_id} not found")
        return {"error": f"Registration {registration_id} not found"}
    
    print(f"DEBUG: Found registration: {reg_check[2]} {reg_check[3]} ({reg_check[1]})")
    
    # Insert test recommendation
    db.execute(
        text("""
            INSERT INTO line_manager_recommendations 
            (registration_id, participant_name, participant_email, line_manager_email, 
             recommendation_text, submitted_at, created_at, recommendation_token, event_id)
            VALUES (:registration_id, :name, :email, 'manager@test.com',
                    'This is a test recommendation for debugging purposes.', 
                    CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, 'test-token-456', 41)
        """),
        {
            "registration_id": registration_id,
            "name": f"{reg_check[2]} {reg_check[3]}",
            "email": reg_check[1]
        }
    )
    
    db.commit()
    print(f"DEBUG: Test recommendation created for registration {registration_id}")
    
    return {"message": f"Test recommendation created for registration {registration_id}"}

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
    
    # Get participant email from event_participants table
    participant_info = db.execute(
        text("SELECT email FROM event_participants WHERE id = :participant_id"),
        {"participant_id": participant_id}
    ).fetchone()
    
    if not participant_info:
        print(f"DEBUG: Participant {participant_id} not found in event_participants")
        raise HTTPException(status_code=404, detail="Participant not found")
    
    participant_email = participant_info[0]
    print(f"DEBUG: Found participant email: {participant_email}")
    
    # Try to find recommendation by participant email and event_id
    result = db.execute(
        text("""
            SELECT id, line_manager_email, recommendation_text, submitted_at, created_at
            FROM line_manager_recommendations 
            WHERE participant_email = :email AND event_id = :event_id
            ORDER BY created_at DESC
            LIMIT 1
        """),
        {"email": participant_email, "event_id": event_id}
    ).fetchone()
    
    print(f"DEBUG: Email match result for {participant_email}: {result}")
    
    if not result:
        print(f"DEBUG: No recommendation found for participant {participant_id} ({participant_email}) in event {event_id}")
        raise HTTPException(status_code=404, detail="No recommendation found for this participant")
    
    print(f"DEBUG: Returning recommendation data: {result}")
    return {
        "id": result[0],
        "line_manager_email": result[1],
        "recommendation_text": result[2],
        "submitted_at": result[3],
        "created_at": result[4]
    }