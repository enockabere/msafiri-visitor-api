from typing import Any, List
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from app import crud, schemas
from app.api import deps
from app.db.database import get_db
from app.models.user import UserRole
from app.schemas.app_feedback import AppFeedbackCreate, AppFeedbackResponse
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

@router.post("/", response_model=AppFeedbackResponse)
async def submit_feedback(
    *,
    request: Request,
    db: Session = Depends(get_db),
    feedback_in: AppFeedbackCreate,
    current_user: schemas.User = Depends(deps.get_current_user),
) -> Any:
    """Submit app feedback (creates new or updates existing)"""
    # Debug raw request body
    body = await request.body()
    logger.info(f"🔥 RAW REQUEST: {body.decode()}")
    
    logger.info(f"🔥 FEEDBACK DEBUG: Received feedback_in: {feedback_in}")
    logger.info(f"🔥 FEEDBACK DEBUG: Category type: {type(feedback_in.category)}")
    logger.info(f"🔥 FEEDBACK DEBUG: Category value: {feedback_in.category}")
    logger.info(f"🔥 FEEDBACK DEBUG: Category repr: {repr(feedback_in.category)}")
    
    # Check if user already has feedback
    existing_feedback = crud.app_feedback.get_by_user_latest(db, user_id=current_user.id)
    
    if existing_feedback:
        # Update existing feedback
        feedback = crud.app_feedback.update_feedback(
            db, feedback=existing_feedback, feedback_in=feedback_in
        )
    else:
        # Create new feedback
        feedback = crud.app_feedback.create_feedback(
            db, feedback_in=feedback_in, user_id=current_user.id
        )
    
    # Mark that user has submitted feedback
    from app.models.feedback_prompt import FeedbackPrompt
    prompt_record = db.query(FeedbackPrompt).filter(
        FeedbackPrompt.user_id == current_user.id
    ).first()
    
    if prompt_record:
        prompt_record.has_submitted_feedback = True
        db.add(prompt_record)
        db.commit()
    
    # Send notification to super admins about new feedback
    try:
        from app.models.user import User, UserRole
        from app.models.notification import Notification, NotificationPriority, NotificationType
        
        # Get all super admins
        super_admins = db.query(User).filter(User.role == UserRole.SUPER_ADMIN).all()
        
        # Create notification for each super admin
        for admin in super_admins:
            notification = Notification(
                user_id=admin.id,
                title="New App Feedback Received",
                message=f"New {feedback_in.rating}-star feedback from {current_user.full_name or current_user.email} in category: {feedback_in.category.value}",
                priority="MEDIUM",
                notification_type=NotificationType.APP_FEEDBACK
            )
            db.add(notification)
        
        db.commit()
        logger.info(f"📧 Sent feedback notifications to {len(super_admins)} super admins")
    except Exception as e:
        logger.error(f"❌ Failed to send feedback notifications: {e}")
        # Don't fail the feedback submission if notification fails
        pass
    
    # Return with user info
    return AppFeedbackResponse(
        id=feedback.id,
        user_id=feedback.user_id,
        rating=feedback.rating,
        category=feedback.category,
        feedback_text=feedback.feedback_text,
        created_at=feedback.created_at,
        updated_at=feedback.updated_at,
        user_email=current_user.email,
        user_name=current_user.full_name
    )

@router.get("/my-feedback", response_model=List[AppFeedbackResponse])
def get_my_feedback(
    db: Session = Depends(get_db),
    current_user: schemas.User = Depends(deps.get_current_user),
    skip: int = 0,
    limit: int = 100,
) -> Any:
    """Get current user's feedback"""
    feedback_list = crud.app_feedback.get_by_user(
        db, user_id=current_user.id, skip=skip, limit=limit
    )
    
    return [
        AppFeedbackResponse(
            id=feedback.id,
            user_id=feedback.user_id,
            rating=feedback.rating,
            category=feedback.category,
            feedback_text=feedback.feedback_text,
            created_at=feedback.created_at,
            updated_at=feedback.updated_at,
            user_email=current_user.email,
            user_name=current_user.full_name
        )
        for feedback in feedback_list
    ]

@router.get("/all", response_model=List[AppFeedbackResponse])
def get_all_feedback(
    db: Session = Depends(get_db),
    current_user: schemas.User = Depends(deps.get_current_user),
    skip: int = 0,
    limit: int = 100,
) -> Any:
    """Get all feedback - Super Admin only"""
    if current_user.role != UserRole.SUPER_ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    
    feedback_list = crud.app_feedback.get_all_with_user_info(
        db, skip=skip, limit=limit
    )
    
    return [
        AppFeedbackResponse(
            id=feedback.id,
            user_id=feedback.user_id,
            rating=feedback.rating,
            category=feedback.category,
            feedback_text=feedback.feedback_text,
            created_at=feedback.created_at,
            updated_at=feedback.updated_at,
            user_email=feedback.user.email if feedback.user else None,
            user_name=feedback.user.full_name if feedback.user else None
        )
        for feedback in feedback_list
    ]

@router.get("/stats")
def get_feedback_stats(
    db: Session = Depends(get_db),
    current_user: schemas.User = Depends(deps.get_current_user),
) -> Any:
    """Get feedback statistics - Super Admin only"""
    if current_user.role != UserRole.SUPER_ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    
    from sqlalchemy import func
    from app.models.app_feedback import AppFeedback, FeedbackCategory
    
    # Get total count
    total_feedback = db.query(func.count(AppFeedback.id)).scalar()
    
    # Get average rating
    avg_rating = crud.app_feedback.get_average_rating(db)
    
    # Get rating distribution
    rating_distribution = crud.app_feedback.get_rating_distribution(db)
    
    # Get category distribution
    category_results = (
        db.query(AppFeedback.category, func.count(AppFeedback.id))
        .group_by(AppFeedback.category)
        .all()
    )
    category_distribution = {category.value: count for category, count in category_results}
    
    return {
        "total_feedback": total_feedback,
        "average_rating": avg_rating,
        "rating_distribution": rating_distribution,
        "category_distribution": category_distribution
    }

@router.get("/should-prompt")
def should_prompt_feedback(
    db: Session = Depends(get_db),
    current_user: schemas.User = Depends(deps.get_current_user),
) -> Any:
    """Check if user should be prompted for feedback"""
    from datetime import datetime, timedelta
    from app.models.feedback_prompt import FeedbackPrompt
    
    # Get or create prompt record
    prompt_record = db.query(FeedbackPrompt).filter(
        FeedbackPrompt.user_id == current_user.id
    ).first()
    
    if not prompt_record:
        # First time user - create record but don't prompt yet
        prompt_record = FeedbackPrompt(
            user_id=current_user.id,
            last_prompted_at=None,
            prompt_count=0,
            dismissed_count=0,
            has_submitted_feedback=False
        )
        db.add(prompt_record)
        db.commit()
        return {"should_prompt": False, "reason": "new_user"}
    
    # Check if user already submitted feedback
    if prompt_record.has_submitted_feedback:
        return {"should_prompt": False, "reason": "already_submitted"}
    
    # Don't prompt if dismissed too many times
    if prompt_record.dismissed_count >= 3:
        return {"should_prompt": False, "reason": "dismissed_too_many"}
    
    # Check time-based prompting
    now = datetime.utcnow()
    
    if prompt_record.last_prompted_at is None:
        # First prompt after 3 days of app usage
        user_created = current_user.created_at
        if now - user_created >= timedelta(days=3):
            return {"should_prompt": True, "reason": "first_prompt"}
    else:
        # Subsequent prompts - wait 7 days between prompts
        if now - prompt_record.last_prompted_at >= timedelta(days=7):
            return {"should_prompt": True, "reason": "periodic_prompt"}
    
    return {"should_prompt": False, "reason": "too_soon"}

@router.post("/mark-prompted")
def mark_feedback_prompted(
    db: Session = Depends(get_db),
    current_user: schemas.User = Depends(deps.get_current_user),
) -> Any:
    """Mark that user was prompted for feedback"""
    from datetime import datetime
    from app.models.feedback_prompt import FeedbackPrompt
    
    prompt_record = db.query(FeedbackPrompt).filter(
        FeedbackPrompt.user_id == current_user.id
    ).first()
    
    if prompt_record:
        prompt_record.last_prompted_at = datetime.utcnow()
        prompt_record.prompt_count += 1
        db.add(prompt_record)
        db.commit()
    
    return {"message": "Prompt recorded"}

@router.post("/mark-dismissed")
def mark_feedback_dismissed(
    db: Session = Depends(get_db),
    current_user: schemas.User = Depends(deps.get_current_user),
) -> Any:
    """Mark that user dismissed feedback prompt"""
    from datetime import datetime
    from app.models.feedback_prompt import FeedbackPrompt
    
    prompt_record = db.query(FeedbackPrompt).filter(
        FeedbackPrompt.user_id == current_user.id
    ).first()
    
    if prompt_record:
        prompt_record.dismissed_count += 1
        prompt_record.last_prompted_at = datetime.utcnow()
        db.add(prompt_record)
        db.commit()
    
    return {"message": "Dismissal recorded"}
