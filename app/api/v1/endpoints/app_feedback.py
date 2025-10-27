from typing import Any, List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app import crud, schemas
from app.api import deps
from app.db.database import get_db
from app.models.user import UserRole
from app.schemas.app_feedback import AppFeedbackCreate, AppFeedbackResponse

router = APIRouter()

@router.post("/", response_model=AppFeedbackResponse)
def create_feedback(
    *,
    db: Session = Depends(get_db),
    feedback_in: AppFeedbackCreate,
    current_user: schemas.User = Depends(deps.get_current_user),
) -> Any:
    """Create new app feedback"""
    feedback = crud.app_feedback.create_feedback(
        db, feedback_in=feedback_in, user_id=current_user.id
    )
    
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