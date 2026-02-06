from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import and_

from app.crud.base import CRUDBase
from app.models.perdiem_request import PerdiemRequest, PerdiemStatus
from app.schemas.perdiem_request import PerdiemRequestCreate, PerdiemRequestUpdate

class CRUDPerdiemRequest(CRUDBase[PerdiemRequest, PerdiemRequestCreate, PerdiemRequestUpdate]):
    def get_by_participant(
        self, db: Session, *, participant_id: int
    ) -> List[PerdiemRequest]:
        return db.query(PerdiemRequest).filter(
            PerdiemRequest.participant_id == participant_id
        ).all()

    def get_by_status(
        self, db: Session, *, status: PerdiemStatus
    ) -> List[PerdiemRequest]:
        return db.query(PerdiemRequest).filter(
            PerdiemRequest.status == status
        ).all()

    def get_pending_approvals(
        self, db: Session, *, manager_email: str
    ) -> List[PerdiemRequest]:
        """Get requests pending approval from a specific manager"""
        return db.query(PerdiemRequest).filter(
            and_(
                PerdiemRequest.status.in_([PerdiemStatus.PENDING, PerdiemStatus.LINE_MANAGER_APPROVED]),
                # This would need to be enhanced with proper manager matching logic
            )
        ).all()

    def approve_by_line_manager(
        self, db: Session, *, request_id: int, approved_by: str, notes: Optional[str] = None
    ) -> Optional[PerdiemRequest]:
        request = self.get(db, id=request_id)
        if request and request.status == PerdiemStatus.PENDING:
            request.status = PerdiemStatus.LINE_MANAGER_APPROVED
            request.line_manager_approved_by = approved_by
            request.admin_notes = notes
            db.commit()
            db.refresh(request)
        return request

    def approve_by_budget_owner(
        self, db: Session, *, request_id: int, approved_by: str, notes: Optional[str] = None
    ) -> Optional[PerdiemRequest]:
        request = self.get(db, id=request_id)
        if request and request.status == PerdiemStatus.LINE_MANAGER_APPROVED:
            request.status = PerdiemStatus.BUDGET_OWNER_APPROVED
            request.budget_owner_approved_by = approved_by
            request.admin_notes = notes
            db.commit()
            db.refresh(request)
        return request

    def reject_request(
        self, db: Session, *, request_id: int, rejected_by: str, reason: str
    ) -> Optional[PerdiemRequest]:
        request = self.get(db, id=request_id)
        if request and request.status in [PerdiemStatus.PENDING, PerdiemStatus.LINE_MANAGER_APPROVED]:
            request.status = PerdiemStatus.REJECTED
            request.rejected_by = rejected_by
            request.rejection_reason = reason
            db.commit()
            db.refresh(request)
        return request

perdiem_request = CRUDPerdiemRequest(PerdiemRequest)
