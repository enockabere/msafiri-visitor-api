from typing import List, Optional
from sqlalchemy.orm import Session, joinedload
from app.crud.base import CRUDBase
from app.models.app_feedback import AppFeedback
from app.models.user import User
from app.schemas.app_feedback import AppFeedbackCreate

class CRUDAppFeedback(CRUDBase[AppFeedback, AppFeedbackCreate, AppFeedbackCreate]):
    def create_feedback(
        self, db: Session, *, feedback_in: AppFeedbackCreate, user_id: int
    ) -> AppFeedback:
        feedback = AppFeedback(
            user_id=user_id,
            rating=feedback_in.rating,
            category=feedback_in.category,
            feedback_text=feedback_in.feedback_text
        )
        db.add(feedback)
        db.commit()
        db.refresh(feedback)
        return feedback
    
    def get_all_with_user_info(
        self, db: Session, *, skip: int = 0, limit: int = 100
    ) -> List[AppFeedback]:
        return (
            db.query(self.model)
            .options(joinedload(AppFeedback.user))
            .order_by(AppFeedback.created_at.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )
    
    def get_by_user(
        self, db: Session, *, user_id: int, skip: int = 0, limit: int = 100
    ) -> List[AppFeedback]:
        return (
            db.query(self.model)
            .filter(AppFeedback.user_id == user_id)
            .order_by(AppFeedback.created_at.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )
    
    def get_average_rating(self, db: Session) -> Optional[float]:
        from sqlalchemy import func
        result = db.query(func.avg(AppFeedback.rating)).scalar()
        return round(result, 2) if result else None
    
    def get_rating_distribution(self, db: Session) -> dict:
        from sqlalchemy import func
        results = (
            db.query(AppFeedback.rating, func.count(AppFeedback.id))
            .group_by(AppFeedback.rating)
            .all()
        )
        return {rating: count for rating, count in results}

app_feedback = CRUDAppFeedback(AppFeedback)