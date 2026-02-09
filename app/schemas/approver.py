from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

class ApprovalStepBase(BaseModel):
    step_order: int
    step_name: Optional[str] = None
    approver_user_id: int

class ApprovalStepCreate(ApprovalStepBase):
    pass

class ApprovalStepResponse(ApprovalStepBase):
    id: int
    workflow_id: int
    approver_name: Optional[str] = None
    approver_email: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True

class ApprovalWorkflowBase(BaseModel):
    workflow_type: str
    name: str
    is_active: bool = True

class ApprovalWorkflowCreate(ApprovalWorkflowBase):
    tenant_id: str
    steps: List[ApprovalStepCreate]

class ApprovalWorkflowUpdate(BaseModel):
    name: Optional[str] = None
    is_active: Optional[bool] = None
    steps: Optional[List[ApprovalStepCreate]] = None

class ApprovalWorkflowResponse(ApprovalWorkflowBase):
    id: int
    tenant_id: str
    steps: List[ApprovalStepResponse]
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True
