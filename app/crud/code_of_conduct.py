# File: app/crud/code_of_conduct.py
from sqlalchemy.orm import Session
from typing import List, Optional
from app.models.code_of_conduct import CodeOfConduct
from app.schemas.code_of_conduct import CodeOfConductCreate, CodeOfConductUpdate

def create_code_of_conduct(
    db: Session, 
    code_data: CodeOfConductCreate, 
    tenant_id: str,
    created_by: str
) -> CodeOfConduct:
    """Create new code of conduct"""
    code = CodeOfConduct(
        title=code_data.title,
        content=code_data.content,
        url=code_data.url,
        document_url=code_data.document_url,
        document_public_id=code_data.document_public_id,
        version=code_data.version,
        effective_date=code_data.effective_date,
        tenant_id=tenant_id,
        created_by=created_by,
        updated_by=created_by  # Set updated_by to avoid None value
    )
    db.add(code)
    db.commit()
    db.refresh(code)
    return code

def get_code_of_conduct_by_tenant(db: Session, tenant_id: str) -> Optional[CodeOfConduct]:
    """Get active code of conduct for tenant"""
    return db.query(CodeOfConduct).filter(
        CodeOfConduct.tenant_id == tenant_id,
        CodeOfConduct.is_active == True
    ).first()

def get_all_codes_by_tenant(db: Session, tenant_id: str) -> List[CodeOfConduct]:
    """Get all codes of conduct for tenant"""
    return db.query(CodeOfConduct).filter(
        CodeOfConduct.tenant_id == tenant_id
    ).order_by(CodeOfConduct.created_at.desc()).all()

def update_code_of_conduct(
    db: Session, 
    code_id: int, 
    code_data: CodeOfConductUpdate,
    updated_by: str
) -> Optional[CodeOfConduct]:
    """Update code of conduct"""
    code = db.query(CodeOfConduct).filter(CodeOfConduct.id == code_id).first()
    if not code:
        return None
    
    update_data = code_data.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(code, field, value)
    
    code.updated_by = updated_by
    db.commit()
    db.refresh(code)
    return code

def delete_code_of_conduct(db: Session, code_id: int) -> bool:
    """Delete code of conduct"""
    code = db.query(CodeOfConduct).filter(CodeOfConduct.id == code_id).first()
    if not code:
        return False
    
    db.delete(code)
    db.commit()
    return True