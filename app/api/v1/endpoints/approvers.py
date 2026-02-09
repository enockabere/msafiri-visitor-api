from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload
from typing import List
from app.db.database import get_db
from app.models.approver import ApprovalWorkflow, ApprovalStep
from app.schemas.approver import ApprovalWorkflowCreate, ApprovalWorkflowUpdate, ApprovalWorkflowResponse
from app.api.deps import get_current_user
from app.models.user import User

router = APIRouter()

@router.post("/workflows", response_model=ApprovalWorkflowResponse)
def create_workflow(
    workflow: ApprovalWorkflowCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new approval workflow with steps"""
    db_workflow = ApprovalWorkflow(
        tenant_id=workflow.tenant_id,
        workflow_type=workflow.workflow_type,
        name=workflow.name,
        is_active=workflow.is_active
    )
    db.add(db_workflow)
    db.flush()

    for step_data in workflow.steps:
        db_step = ApprovalStep(
            workflow_id=db_workflow.id,
            step_order=step_data.step_order,
            step_name=step_data.step_name,
            approver_user_id=step_data.approver_user_id
        )
        db.add(db_step)

    db.commit()
    db.refresh(db_workflow)
    
    # Load with relationships
    workflow_with_steps = db.query(ApprovalWorkflow).options(
        joinedload(ApprovalWorkflow.steps).joinedload(ApprovalStep.approver)
    ).filter(ApprovalWorkflow.id == db_workflow.id).first()
    
    # Format response
    response = ApprovalWorkflowResponse.model_validate(workflow_with_steps)
    for i, step in enumerate(response.steps):
        if workflow_with_steps.steps[i].approver:
            step.approver_name = workflow_with_steps.steps[i].approver.full_name
            step.approver_email = workflow_with_steps.steps[i].approver.email
    
    return response

@router.get("/workflows/{tenant_id}", response_model=List[ApprovalWorkflowResponse])
def get_workflows(
    tenant_id: str,
    workflow_type: str = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get all workflows for a tenant, optionally filtered by type"""
    query = db.query(ApprovalWorkflow).options(
        joinedload(ApprovalWorkflow.steps).joinedload(ApprovalStep.approver)
    ).filter(ApprovalWorkflow.tenant_id == tenant_id)
    
    if workflow_type:
        query = query.filter(ApprovalWorkflow.workflow_type == workflow_type)
    
    workflows = query.all()
    
    # Format response
    result = []
    for workflow in workflows:
        response = ApprovalWorkflowResponse.model_validate(workflow)
        for i, step in enumerate(response.steps):
            if workflow.steps[i].approver:
                step.approver_name = workflow.steps[i].approver.full_name
                step.approver_email = workflow.steps[i].approver.email
        result.append(response)
    
    return result

@router.put("/workflows/{workflow_id}", response_model=ApprovalWorkflowResponse)
def update_workflow(
    workflow_id: int,
    workflow_update: ApprovalWorkflowUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update an approval workflow"""
    db_workflow = db.query(ApprovalWorkflow).filter(ApprovalWorkflow.id == workflow_id).first()
    if not db_workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")
    
    if workflow_update.name is not None:
        db_workflow.name = workflow_update.name
    if workflow_update.is_active is not None:
        db_workflow.is_active = workflow_update.is_active
    
    if workflow_update.steps is not None:
        # Delete existing steps
        db.query(ApprovalStep).filter(ApprovalStep.workflow_id == workflow_id).delete()
        
        # Add new steps
        for step_data in workflow_update.steps:
            db_step = ApprovalStep(
                workflow_id=workflow_id,
                step_order=step_data.step_order,
                step_name=step_data.step_name,
                approver_user_id=step_data.approver_user_id
            )
            db.add(db_step)
    
    db.commit()
    
    # Load with relationships
    workflow_with_steps = db.query(ApprovalWorkflow).options(
        joinedload(ApprovalWorkflow.steps).joinedload(ApprovalStep.approver)
    ).filter(ApprovalWorkflow.id == workflow_id).first()
    
    # Format response
    response = ApprovalWorkflowResponse.model_validate(workflow_with_steps)
    for i, step in enumerate(response.steps):
        if workflow_with_steps.steps[i].approver:
            step.approver_name = workflow_with_steps.steps[i].approver.full_name
            step.approver_email = workflow_with_steps.steps[i].approver.email
    
    return response

@router.delete("/workflows/{workflow_id}")
def delete_workflow(
    workflow_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete an approval workflow"""
    db_workflow = db.query(ApprovalWorkflow).filter(ApprovalWorkflow.id == workflow_id).first()
    if not db_workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")
    
    db.delete(db_workflow)
    db.commit()
    
    return {"message": "Workflow deleted successfully"}

@router.get("/users/{tenant_id}", response_model=List[dict])
def get_tenant_users(
    tenant_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get all users for a tenant (for approver selection)"""
    from app.models.user import UserRole
    
    users = db.query(User).join(UserRole).filter(
        UserRole.tenant_id == tenant_id
    ).all()
    
    return [{"id": u.id, "full_name": u.full_name, "email": u.email} for u in users]
