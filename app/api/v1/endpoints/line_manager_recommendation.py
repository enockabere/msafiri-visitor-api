from fastapi import APIRouter, Depends, HTTPException, Query
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
    is_recommended: bool

@router.get("/debug/token/{token}")
async def debug_token_lookup(
    token: str,
    db: Session = Depends(get_db)
):
    """DEBUG: Check if token exists in database"""
    
    logger.info(f"🔍 DEBUG: Looking up token {token}")
    
    # Check if token exists
    result = db.execute(
        text("""
            SELECT id, participant_name, participant_email, contact_type, 
                   recommendation_token, event_id, created_at
            FROM line_manager_recommendations 
            WHERE recommendation_token = :token
        """),
        {"token": token}
    ).fetchone()
    
    if result:
        logger.info(f"🔍 DEBUG: Token found - ID: {result[0]}, Contact Type: {result[3]}")
        return {
            "token_found": True,
            "id": result[0],
            "participant_name": result[1],
            "participant_email": result[2],
            "contact_type": result[3],
            "event_id": result[5],
            "created_at": str(result[6])
        }
    else:
        logger.info(f"🔍 DEBUG: Token NOT found")
        return {"token_found": False}

@router.get("/debug/create-test-token/{contact_type}")
async def create_test_token(
    contact_type: str,
    db: Session = Depends(get_db)
):
    """DEBUG: Create a test recommendation token for testing"""
    
    import uuid
    from sqlalchemy import text
    
    # Generate test token
    test_token = str(uuid.uuid4())
    
    # Insert test recommendation
    db.execute(
        text("""
            INSERT INTO line_manager_recommendations 
            (registration_id, participant_name, participant_email, line_manager_email, 
             operation_center, event_title, event_dates, event_location,
             created_at, recommendation_token, event_id, contact_type)
            VALUES (1, 'Test User', 'test@example.com', 'manager@test.com',
                    'OCA', 'Test Event', '2026-02-01 to 2026-02-05', 'Test Location',
                    CURRENT_TIMESTAMP, :token, 1, :contact_type)
        """),
        {
            "token": test_token,
            "contact_type": contact_type
        }
    )
    
    db.commit()
    
    base_url = "http://41.90.17.25:3000"
    if contact_type == "HRCO":
        test_url = f"{base_url}/public/hrco-recommendation/{test_token}"
    elif contact_type == "Career Manager":
        test_url = f"{base_url}/public/career-manager-recommendation/{test_token}"
    else:
        test_url = f"{base_url}/public/line-manager-recommendation/{test_token}"
    
    return {
        "message": f"Test {contact_type} recommendation created",
        "token": test_token,
        "test_url": test_url
    }

@router.get("/debug/all-tokens")
async def debug_all_tokens(db: Session = Depends(get_db)):
    """DEBUG: List all recommendation tokens"""
    
    results = db.execute(
        text("""
            SELECT recommendation_token, contact_type, participant_name, created_at
            FROM line_manager_recommendations 
            ORDER BY created_at DESC
            LIMIT 10
        """)
    ).fetchall()
    
    tokens = []
    for result in results:
        tokens.append({
            "token": result[0],
            "contact_type": result[1],
            "participant_name": result[2],
            "created_at": str(result[3])
        })
    
    logger.info(f"🔍 DEBUG: Found {len(tokens)} tokens")
    return {"tokens": tokens}

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
    
    logger.info(f"🔍 Getting recommendation details for token: {token}")
    
    result = db.execute(
        text("""
            SELECT r.id, r.participant_name, r.participant_email, r.operation_center,
                   r.event_title, r.event_dates, r.event_location, r.is_recommended,
                   r.submitted_at, e.registration_deadline, r.contact_type
            FROM line_manager_recommendations r
            JOIN events e ON r.event_id = e.id
            WHERE r.recommendation_token = :token
        """),
        {"token": token}
    ).fetchone()
    
    logger.info(f"🔍 Database query result: {result}")
    
    if not result:
        logger.error(f"🔍 No recommendation found for token: {token}")
        raise HTTPException(status_code=404, detail="Recommendation request not found")
    
    return {
        "id": result[0],
        "participant_name": result[1],
        "participant_email": result[2],
        "operation_center": result[3],
        "event_title": result[4],
        "event_dates": result[5],
        "event_location": result[6],
        "is_recommended": result[7],
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
            SET is_recommended = :is_recommended, submitted_at = CURRENT_TIMESTAMP
            WHERE recommendation_token = :token
        """),
        {"is_recommended": submission.is_recommended, "token": token}
    )
    
    db.commit()
    
    logger.info(f"Recommendation submitted for token {token}")
    
    return {"message": "Recommendation submitted successfully"}

@router.get("/debug/all")
async def debug_all_recommendations(db: Session = Depends(get_db)):
    """DEBUG: Print all recommendations in database"""
    
    logger.info("DEBUG: ALL RECOMMENDATIONS IN DATABASE")
    
    all_recs = db.execute(
        text("""
            SELECT id, registration_id, participant_name, participant_email, 
                   line_manager_email, is_recommended, submitted_at, created_at,
                   recommendation_token, event_id
            FROM line_manager_recommendations 
            ORDER BY created_at DESC
        """)
    ).fetchall()
    
    logger.info(f"DEBUG: Total recommendations: {len(all_recs)}")
    
    for i, rec in enumerate(all_recs, 1):
        logger.info(f"DEBUG: Recommendation #{i}: ID={rec[0]}, Email={rec[3]}, Event={rec[9]}")
    
    return {"total_recommendations": len(all_recs), "data": "Check server logs"}

@router.get("/debug/match-emails/{participant_id}")
async def debug_email_match(
    participant_id: int,
    db: Session = Depends(get_db)
):
    """DEBUG: Check email matching for participant"""
    
    logger.info(f"DEBUG: Email matching for participant {participant_id}")
    
    # Get participant email from event_participants
    participant_info = db.execute(
        text("SELECT email, full_name FROM event_participants WHERE id = :id"),
        {"id": participant_id}
    ).fetchone()
    
    if participant_info:
        email = participant_info[0]
        name = participant_info[1]
        logger.info(f"DEBUG: Participant {participant_id}: {name} ({email})")
        
        # Check if recommendation exists for this email
        rec_check = db.execute(
            text("SELECT id, is_recommended, submitted_at FROM line_manager_recommendations WHERE participant_email = :email AND event_id = 41"),
            {"email": email}
        ).fetchone()
        
        if rec_check:
            logger.info(f"DEBUG: Found recommendation: ID {rec_check[0]}, submitted {rec_check[2]}")
            return {"participant": f"{name} ({email})", "recommendation_found": True, "rec_id": rec_check[0]}
        else:
            logger.info(f"DEBUG: No recommendation found for {email}")
            return {"participant": f"{name} ({email})", "recommendation_found": False}
    else:
        logger.info(f"DEBUG: Participant {participant_id} not found")
        return {"error": f"Participant {participant_id} not found"}

@router.get("/debug/registrations")
async def debug_registrations(db: Session = Depends(get_db)):
    """DEBUG: Show all public registrations"""
    
    logger.info("DEBUG: ALL PUBLIC REGISTRATIONS")
    
    registrations = db.execute(
        text("""
            SELECT id, event_id, first_name, last_name, personal_email, created_at
            FROM public_registrations 
            WHERE event_id = 41
            ORDER BY created_at DESC
        """)
    ).fetchall()
    
    logger.info(f"DEBUG: Total registrations for event 41: {len(registrations)}")
    
    for i, reg in enumerate(registrations, 1):
        logger.info(f"DEBUG: Registration #{i}: ID={reg[0]}, Name={reg[2]} {reg[3]}, Email={reg[4]}")
    
    return {"total_registrations": len(registrations), "data": "Check server logs"}

@router.get("/debug/user-registration/{email}")
async def debug_user_registration(
    email: str,
    db: Session = Depends(get_db)
):
    """DEBUG: Print registration details for a specific user"""
    
    logger.info(f"DEBUG: Registration details for {email}")
    
    # Get participant from event_participants
    participant = db.execute(
        text("SELECT * FROM event_participants WHERE email = :email"),
        {"email": email}
    ).fetchone()
    
    if participant:
        logger.info(f"EVENT PARTICIPANT RECORD found for {email}")
        
        # Get public registration details
        pub_reg = db.execute(
            text("SELECT * FROM public_registrations WHERE participant_id = :pid"),
            {"pid": participant.id}
        ).fetchone()
        
        if pub_reg:
            logger.info(f"PUBLIC REGISTRATION RECORD found for participant {participant.id}")
        else:
            logger.info(f"NO PUBLIC REGISTRATION RECORD FOUND for participant {participant.id}")
        
        return {
            "participant_found": True,
            "participant_id": participant.id,
            "public_registration_found": pub_reg is not None,
            "details": "Check server logs for full details"
        }
    else:
        logger.info(f"NO PARTICIPANT FOUND with email {email}")
        return {"participant_found": False}

@router.get("/debug/create-test-for-email/{participant_id}")
async def create_test_for_participant_email(
    participant_id: int,
    db: Session = Depends(get_db)
):
    """DEBUG: Create test recommendation for participant email"""
    
    logger.info(f"DEBUG: Creating test recommendation for participant {participant_id}")
    
    # Get participant info
    participant_info = db.execute(
        text("SELECT email, full_name FROM event_participants WHERE id = :id"),
        {"id": participant_id}
    ).fetchone()
    
    if not participant_info:
        return {"error": f"Participant {participant_id} not found"}
    
    email = participant_info[0]
    name = participant_info[1]
    logger.info(f"DEBUG: Creating recommendation for {name} ({email})")
    
    # Insert test recommendation
    db.execute(
        text("""
            INSERT INTO line_manager_recommendations 
            (registration_id, participant_name, participant_email, line_manager_email, 
             is_recommended, submitted_at, created_at, recommendation_token, event_id)
            VALUES (1, :name, :email, 'test-manager@msf.org',
                    TRUE, 
                    CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, :token, 41)
        """),
        {
            "name": name,
            "email": email,
            "token": f"test-{participant_id}-{int(time.time())}"
        }
    )
    
    db.commit()
    logger.info(f"DEBUG: Test recommendation created for {name} ({email})")
    
    return {"message": f"Test recommendation created for {name} ({email})"}

@router.get("/debug/create-test/{registration_id}")
async def create_test_recommendation(
    registration_id: int,
    db: Session = Depends(get_db)
):
    """DEBUG: Create test recommendation for registration"""
    
    logger.info(f"DEBUG: Creating test recommendation for registration {registration_id}")
    
    # Check if registration exists
    reg_check = db.execute(
        text("SELECT id, personal_email, first_name, last_name FROM public_registrations WHERE id = :id"),
        {"id": registration_id}
    ).fetchone()
    
    if not reg_check:
        logger.info(f"DEBUG: Registration {registration_id} not found")
        return {"error": f"Registration {registration_id} not found"}
    
    logger.info(f"DEBUG: Found registration: {reg_check[2]} {reg_check[3]} ({reg_check[1]})")
    
    # Insert test recommendation
    db.execute(
        text("""
            INSERT INTO line_manager_recommendations 
            (registration_id, participant_name, participant_email, line_manager_email, 
             is_recommended, submitted_at, created_at, recommendation_token, event_id)
            VALUES (:registration_id, :name, :email, 'manager@test.com',
                    TRUE, 
                    CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, 'test-token-456', 41)
        """),
        {
            "registration_id": registration_id,
            "name": f"{reg_check[2]} {reg_check[3]}",
            "email": reg_check[1]
        }
    )
    
    db.commit()
    logger.info(f"DEBUG: Test recommendation created for registration {registration_id}")
    
    return {"message": f"Test recommendation created for registration {registration_id}"}

@router.get("/debug/delete-all-participants")
async def delete_all_participants_debug(
    db: Session = Depends(get_db)
):
    """DEBUG: Delete all participants and related data"""
    
    logger.info("STARTING DELETION OF ALL PARTICIPANTS")
    
    try:
        from sqlalchemy import text
        
        # Delete in correct order to avoid foreign key constraints
        tables_to_clean = [
            "line_manager_recommendations",
            "form_responses", 
            "accommodation_allocations",
            "participant_qr_codes",
            "event_participants"
        ]
        
        total_deleted = 0
        results = []
        
        for table in tables_to_clean:
            try:
                # Get count first
                count_result = db.execute(text(f"SELECT COUNT(*) FROM {table}"))
                count = count_result.scalar()
                
                if count > 0:
                    logger.info(f"Deleting {count} records from {table}...")
                    db.execute(text(f"DELETE FROM {table}"))
                    total_deleted += count
                    results.append(f"Deleted {count} records from {table}")
                    logger.info(f"Deleted {count} records from {table}")
                else:
                    results.append(f"No records found in {table}")
                    logger.info(f"No records found in {table}")
                    
            except Exception as e:
                error_msg = f"Could not clean {table}: {e}"
                results.append(error_msg)
                logger.error(f"ERROR: {error_msg}")
        
        # Commit all deletions
        db.commit()
        
        logger.info(f"DELETION COMPLETE! Total records deleted: {total_deleted}")
        
        return {
            "message": "All participants and related data deleted successfully",
            "total_deleted": total_deleted,
            "details": results
        }
        
    except Exception as e:
        db.rollback()
        error_msg = f"ERROR during deletion: {e}"
        logger.error(f"ERROR: {error_msg}")
        raise HTTPException(status_code=500, detail=error_msg)

@router.get("/participant/{participant_id}")
async def get_recommendations_by_participant(
    participant_id: int,
    event_id: Optional[int] = Query(None),
    db: Session = Depends(get_db)
):
    """Get all recommendations (HRCO, Career Manager, Line Manager) by participant ID and event ID"""
    
    logger.info(f"Getting recommendations for participant {participant_id}, event {event_id}")
    
    try:
        # Get participant email from event_participants table
        participant_info = db.execute(
            text("SELECT email, event_id FROM event_participants WHERE id = :participant_id"),
            {"participant_id": participant_id}
        ).fetchone()
        
        if not participant_info:
            logger.info(f"Participant {participant_id} not found")
            return {
                "recommendations": [],
                "message": "Participant not found"
            }
        
        participant_email = participant_info[0]
        participant_event_id = participant_info[1]
        
        # Use event_id from query param or participant's event_id
        search_event_id = event_id if event_id is not None else participant_event_id
        
        logger.info(f"Searching for recommendations - Email: {participant_email}, Event: {search_event_id}")
        
        # Get all recommendations for this participant and event
        results = db.execute(
            text("""
                SELECT id, line_manager_email, contact_type, is_recommended, submitted_at, created_at
                FROM line_manager_recommendations 
                WHERE participant_email = :email AND event_id = :event_id
                ORDER BY created_at DESC
            """),
            {"email": participant_email, "event_id": search_event_id}
        ).fetchall()
        
        recommendations = []
        for result in results:
            recommendations.append({
                "id": result[0],
                "email": result[1],
                "contact_type": result[2] or "Line Manager",  # Default for old records
                "is_recommended": result[3],
                "submitted_at": result[4],
                "created_at": result[5]
            })
        
        logger.info(f"Found {len(recommendations)} recommendations for participant {participant_id}")
        return {
            "recommendations": recommendations,
            "total_count": len(recommendations)
        }
        
    except Exception as e:
        logger.error(f"Error getting recommendations for participant {participant_id}: {str(e)}")
        # Return empty response instead of raising exception to avoid frontend errors
        return {
            "recommendations": [],
            "message": "Error retrieving recommendations"
        }