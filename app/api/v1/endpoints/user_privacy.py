from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import List
import os
import uuid
import json
from datetime import datetime
from app.db.database import get_db
from app.models.user_profile import UserProfile, DataDeletionLog
from app.models.user import User
from app.models.event_participant import EventParticipant
from app.models.visitor_enhancements import ParticipantProfile
from app.api.deps import get_current_user

router = APIRouter()

UPLOAD_DIR = "uploads/profile_images"
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif"}
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB

# Ensure upload directory exists
os.makedirs(UPLOAD_DIR, exist_ok=True)

@router.post("/upload-profile-image")
def upload_profile_image(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """User uploads profile image"""
    
    # Validate file
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file provided")
    
    file_ext = os.path.splitext(file.filename)[1].lower()
    if file_ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail="Invalid file type. Only JPG, PNG, GIF allowed")
    
    # Check file size
    file.file.seek(0, 2)  # Seek to end
    file_size = file.file.tell()
    file.file.seek(0)  # Reset to beginning
    
    if file_size > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="File too large. Maximum 5MB allowed")
    
    # Generate unique filename
    unique_filename = f"{uuid.uuid4()}{file_ext}"
    file_path = os.path.join(UPLOAD_DIR, unique_filename)
    
    # Save file
    try:
        with open(file_path, "wb") as buffer:
            content = file.file.read()
            buffer.write(content)
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to save file")
    
    # Update or create user profile
    profile = db.query(UserProfile).filter(UserProfile.user_id == current_user.id).first()
    
    if profile:
        # Delete old image if exists
        if profile.profile_image_filename:
            old_path = os.path.join(UPLOAD_DIR, profile.profile_image_filename)
            if os.path.exists(old_path):
                os.remove(old_path)
        
        profile.profile_image_filename = unique_filename
        profile.profile_image_url = f"/uploads/profile_images/{unique_filename}"
    else:
        profile = UserProfile(
            user_id=current_user.id,
            profile_image_filename=unique_filename,
            profile_image_url=f"/uploads/profile_images/{unique_filename}"
        )
        db.add(profile)
    
    db.commit()
    db.refresh(profile)
    
    return {
        "message": "Profile image uploaded successfully",
        "image_url": profile.profile_image_url
    }

@router.get("/profile-image")
def get_profile_image(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get user's profile image URL"""
    
    profile = db.query(UserProfile).filter(UserProfile.user_id == current_user.id).first()
    
    if not profile or not profile.profile_image_url:
        return {"image_url": None}
    
    return {"image_url": profile.profile_image_url}

@router.delete("/delete-personal-data")
def delete_personal_data(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete user's personal data while keeping audit trail"""
    
    try:
        affected_tables = []
        deletion_summary = []
        
        # 1. Anonymize user data
        current_user.full_name = f"User_{current_user.id}"
        current_user.phone = None
        affected_tables.append("users")
        deletion_summary.append("Anonymized name and phone")
        
        # 2. Delete participant profiles (allergies, medical info, etc.)
        participant_profiles = db.query(ParticipantProfile).join(
            EventParticipant, ParticipantProfile.participant_id == EventParticipant.id
        ).filter(EventParticipant.email == current_user.email).all()
        
        for profile in participant_profiles:
            profile.dietary_restrictions = None
            profile.food_allergies = None
            profile.medical_conditions = None
            profile.mobility_requirements = None
            profile.special_requests = None
            profile.emergency_contact_name = None
            profile.emergency_contact_phone = None
            profile.emergency_contact_relationship = None
        
        if participant_profiles:
            affected_tables.append("participant_profiles")
            deletion_summary.append(f"Cleared {len(participant_profiles)} participant profiles")
        
        # 3. Anonymize event participants (keep email for audit but clear personal data)
        participants = db.query(EventParticipant).filter(
            EventParticipant.email == current_user.email
        ).all()
        
        for participant in participants:
            participant.full_name = f"Participant_{participant.id}"
            participant.phone = None
            participant.organization = "Deleted"
            participant.job_title = "Deleted"
        
        if participants:
            affected_tables.append("event_participants")
            deletion_summary.append(f"Anonymized {len(participants)} event participations")
        
        # 4. Delete profile image
        profile = db.query(UserProfile).filter(UserProfile.user_id == current_user.id).first()
        if profile:
            if profile.profile_image_filename:
                file_path = os.path.join(UPLOAD_DIR, profile.profile_image_filename)
                if os.path.exists(file_path):
                    os.remove(file_path)
            
            profile.profile_image_url = None
            profile.profile_image_filename = None
            profile.data_deleted = True
            profile.data_deleted_at = datetime.now()
            
            affected_tables.append("user_profiles")
            deletion_summary.append("Deleted profile image")
        
        # 5. Anonymize chat messages (keep for audit but remove personal content)
        db.execute(text("""
            UPDATE chat_messages 
            SET sender_name = CONCAT('User_', :user_id), message = '[Message deleted by user]'
            WHERE sender_email = :email
        """), {"user_id": current_user.id, "email": current_user.email})
        
        affected_tables.append("chat_messages")
        deletion_summary.append("Anonymized chat messages")
        
        # 6. Anonymize direct messages
        db.execute(text("""
            UPDATE direct_messages 
            SET sender_name = CONCAT('User_', :user_id), message = '[Message deleted by user]'
            WHERE sender_email = :email
        """), {"user_id": current_user.id, "email": current_user.email})
        
        db.execute(text("""
            UPDATE direct_messages 
            SET recipient_name = CONCAT('User_', :user_id), message = '[Message deleted by user]'
            WHERE recipient_email = :email
        """), {"user_id": current_user.id, "email": current_user.email})
        
        affected_tables.append("direct_messages")
        deletion_summary.append("Anonymized direct messages")
        
        # 7. Keep audit trail records but anonymize personal references
        # (Keep perdiem, equipment requests, reviews, etc. for audit but anonymized)
        
        # 8. Log the deletion
        deletion_log = DataDeletionLog(
            user_email=current_user.email,
            user_id=current_user.id,
            deletion_type="personal_data",
            tables_affected=json.dumps(affected_tables),
            deletion_summary=json.dumps(deletion_summary),
            can_restore=False  # Personal data cannot be restored
        )
        db.add(deletion_log)
        
        db.commit()
        
        return {
            "message": "Personal data deleted successfully",
            "summary": {
                "tables_affected": affected_tables,
                "actions_taken": deletion_summary,
                "note": "Your account remains active but personal data has been removed. Audit records are preserved for compliance."
            }
        }
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to delete personal data: {str(e)}")

@router.get("/data-deletion-status")
def get_data_deletion_status(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Check if user has deleted their personal data"""
    
    profile = db.query(UserProfile).filter(UserProfile.user_id == current_user.id).first()
    
    deletion_log = db.query(DataDeletionLog).filter(
        DataDeletionLog.user_email == current_user.email
    ).order_by(DataDeletionLog.created_at.desc()).first()
    
    return {
        "data_deleted": profile.data_deleted if profile else False,
        "deletion_date": profile.data_deleted_at if profile else None,
        "deletion_log": {
            "deletion_type": deletion_log.deletion_type if deletion_log else None,
            "summary": json.loads(deletion_log.deletion_summary) if deletion_log and deletion_log.deletion_summary else None,
            "can_restore": deletion_log.can_restore if deletion_log else None
        } if deletion_log else None
    }

@router.post("/restore-account")
def restore_account_access(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Restore account access (user can return but without personal data)"""
    
    # Check if data was deleted
    profile = db.query(UserProfile).filter(UserProfile.user_id == current_user.id).first()
    
    if not profile or not profile.data_deleted:
        raise HTTPException(status_code=400, detail="No data deletion found")
    
    # User can continue using the account but personal data remains deleted
    # This is just to confirm they understand their data is gone
    
    return {
        "message": "Account access confirmed",
        "note": "Your account is active but personal data remains deleted for privacy. You can participate in new events with fresh data."
    }