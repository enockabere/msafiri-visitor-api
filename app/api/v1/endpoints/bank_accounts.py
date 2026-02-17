"""API endpoints for user bank accounts."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app.db.database import get_db
from app.models.user import User
from app.models.user_bank_account import UserBankAccount
from app.schemas.bank_account import BankAccountCreate, BankAccountUpdate, BankAccountResponse
from app.core.deps import get_current_user
from app.core.encryption import encryption_service

router = APIRouter()


@router.get("/bank-accounts", response_model=List[BankAccountResponse])
async def get_user_bank_accounts(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all bank accounts for current user."""
    accounts = db.query(UserBankAccount).filter(
        UserBankAccount.user_id == current_user.id,
        UserBankAccount.is_active == True
    ).all()
    
    # Decrypt sensitive fields
    result = []
    for account in accounts:
        try:
            result.append(BankAccountResponse(
                id=account.id,
                bank_name=encryption_service.decrypt(account.bank_name_encrypted),
                account_name=encryption_service.decrypt(account.account_name_encrypted),
                account_number=encryption_service.decrypt(account.account_number_encrypted),
                branch_name=encryption_service.decrypt(account.branch_name_encrypted) if account.branch_name_encrypted else None,
                swift_code=encryption_service.decrypt(account.swift_code_encrypted) if account.swift_code_encrypted else None,
                currency=account.currency,
                is_primary=account.is_primary,
                is_active=account.is_active,
                created_at=account.created_at,
                updated_at=account.updated_at
            ))
        except Exception as e:
            # Skip accounts that can't be decrypted (wrong encryption key)
            print(f"Warning: Could not decrypt bank account {account.id}: {e}")
            continue
    
    return result


@router.post("/bank-accounts", response_model=BankAccountResponse)
async def create_bank_account(
    account_data: BankAccountCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new bank account."""
    # If this is set as primary, unset other primary accounts
    if account_data.is_primary:
        db.query(UserBankAccount).filter(
            UserBankAccount.user_id == current_user.id
        ).update({"is_primary": False})
    
    # Create new account with encrypted fields
    new_account = UserBankAccount(
        user_id=current_user.id,
        bank_name_encrypted=encryption_service.encrypt(account_data.bank_name),
        account_name_encrypted=encryption_service.encrypt(account_data.account_name),
        account_number_encrypted=encryption_service.encrypt(account_data.account_number),
        branch_name_encrypted=encryption_service.encrypt(account_data.branch_name) if account_data.branch_name else None,
        swift_code_encrypted=encryption_service.encrypt(account_data.swift_code) if account_data.swift_code else None,
        currency=account_data.currency,
        is_primary=account_data.is_primary
    )
    
    db.add(new_account)
    db.commit()
    db.refresh(new_account)
    
    return BankAccountResponse(
        id=new_account.id,
        bank_name=account_data.bank_name,
        account_name=account_data.account_name,
        account_number=account_data.account_number,
        branch_name=account_data.branch_name,
        swift_code=account_data.swift_code,
        currency=new_account.currency,
        is_primary=new_account.is_primary,
        is_active=new_account.is_active,
        created_at=new_account.created_at,
        updated_at=new_account.updated_at
    )


@router.put("/bank-accounts/{account_id}", response_model=BankAccountResponse)
async def update_bank_account(
    account_id: int,
    account_data: BankAccountUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update a bank account."""
    account = db.query(UserBankAccount).filter(
        UserBankAccount.id == account_id,
        UserBankAccount.user_id == current_user.id
    ).first()
    
    if not account:
        raise HTTPException(status_code=404, detail="Bank account not found")
    
    # If setting as primary, unset other primary accounts
    if account_data.is_primary:
        db.query(UserBankAccount).filter(
            UserBankAccount.user_id == current_user.id,
            UserBankAccount.id != account_id
        ).update({"is_primary": False})
    
    # Update encrypted fields
    if account_data.bank_name:
        account.bank_name_encrypted = encryption_service.encrypt(account_data.bank_name)
    if account_data.account_name:
        account.account_name_encrypted = encryption_service.encrypt(account_data.account_name)
    if account_data.account_number:
        account.account_number_encrypted = encryption_service.encrypt(account_data.account_number)
    if account_data.branch_name is not None:
        account.branch_name_encrypted = encryption_service.encrypt(account_data.branch_name) if account_data.branch_name else None
    if account_data.swift_code is not None:
        account.swift_code_encrypted = encryption_service.encrypt(account_data.swift_code) if account_data.swift_code else None
    
    # Update non-encrypted fields
    if account_data.currency:
        account.currency = account_data.currency
    if account_data.is_primary is not None:
        account.is_primary = account_data.is_primary
    if account_data.is_active is not None:
        account.is_active = account_data.is_active
    
    db.commit()
    db.refresh(account)
    
    return BankAccountResponse(
        id=account.id,
        bank_name=encryption_service.decrypt(account.bank_name_encrypted),
        account_name=encryption_service.decrypt(account.account_name_encrypted),
        account_number=encryption_service.decrypt(account.account_number_encrypted),
        branch_name=encryption_service.decrypt(account.branch_name_encrypted) if account.branch_name_encrypted else None,
        swift_code=encryption_service.decrypt(account.swift_code_encrypted) if account.swift_code_encrypted else None,
        currency=account.currency,
        is_primary=account.is_primary,
        is_active=account.is_active,
        created_at=account.created_at,
        updated_at=account.updated_at
    )


@router.delete("/bank-accounts/{account_id}")
async def delete_bank_account(
    account_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Soft delete a bank account."""
    account = db.query(UserBankAccount).filter(
        UserBankAccount.id == account_id,
        UserBankAccount.user_id == current_user.id
    ).first()
    
    if not account:
        raise HTTPException(status_code=404, detail="Bank account not found")
    
    account.is_active = False
    db.commit()
    
    return {"message": "Bank account deleted successfully"}
