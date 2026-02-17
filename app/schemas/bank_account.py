"""Schemas for user bank accounts."""
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class BankAccountBase(BaseModel):
    """Base schema for bank account."""
    bank_name: str = Field(..., min_length=1, max_length=200)
    account_name: str = Field(..., min_length=1, max_length=200)
    account_number: str = Field(..., min_length=1, max_length=50)
    branch_name: Optional[str] = Field(None, max_length=200)
    swift_code: Optional[str] = Field(None, max_length=20)
    currency: str = Field(..., pattern="^(USD|EUR|KES)$")
    is_primary: bool = False


class BankAccountCreate(BankAccountBase):
    """Schema for creating a bank account."""
    pass


class BankAccountUpdate(BaseModel):
    """Schema for updating a bank account."""
    bank_name: Optional[str] = Field(None, min_length=1, max_length=200)
    account_name: Optional[str] = Field(None, min_length=1, max_length=200)
    account_number: Optional[str] = Field(None, min_length=1, max_length=50)
    branch_name: Optional[str] = Field(None, max_length=200)
    swift_code: Optional[str] = Field(None, max_length=20)
    currency: Optional[str] = Field(None, pattern="^(USD|EUR|KES)$")
    is_primary: Optional[bool] = None
    is_active: Optional[bool] = None


class BankAccountResponse(BaseModel):
    """Schema for bank account response (decrypted)."""
    id: int
    bank_name: str
    account_name: str
    account_number: str
    branch_name: Optional[str]
    swift_code: Optional[str]
    currency: str
    is_primary: bool
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
