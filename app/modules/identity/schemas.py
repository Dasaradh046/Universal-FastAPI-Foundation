"""
Pydantic schemas for the identity module.
"""
from __future__ import annotations

from pydantic import BaseModel, Field, ConfigDict
from typing import Optional
from datetime import datetime
from uuid import UUID


class TenantBase(BaseModel):
    """Base tenant model."""
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=1000)
    
    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
    )


class TenantCreate(TenantBase):
    """Model for creating a tenant."""
    pass


class TenantUpdate(BaseModel):
    """Model for updating a tenant."""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=1000)
    
    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
    )


class TenantInDBBase(TenantBase):
    """Base model for tenant stored in DB."""
    id: UUID
    is_active: bool
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(
        from_attributes=True,
    )


class TenantResponse(TenantInDBBase):
    """Model for tenant returned to client."""
    pass


class TenantInDB(TenantInDBBase):
    """Model for tenant stored in DB."""
    pass


class UserBase(BaseModel):
    """Base user model."""
    email: str = Field(..., max_length=255)
    first_name: Optional[str] = Field(None, max_length=100)
    last_name: Optional[str] = Field(None, max_length=100)
    is_active: Optional[bool] = Field(None)
    is_superuser: Optional[bool] = Field(None)
    
    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
    )


class UserCreate(UserBase):
    """Model for creating a user."""
    password: str = Field(..., min_length=8)
    
    
class UserUpdate(BaseModel):
    """Model for updating a user."""
    email: Optional[str] = Field(None, max_length=255)
    first_name: Optional[str] = Field(None, max_length=100)
    last_name: Optional[str] = Field(None, max_length=100)
    is_active: Optional[bool] = Field(None)
    is_superuser: Optional[bool] = Field(None)
    password: Optional[str] = Field(None, min_length=8)
    
    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
    )


class UserInDBBase(UserBase):
    """Base model for user stored in DB."""
    id: UUID
    tenant_id: UUID
    password_hash: str  # Hashed password, never return this in responses
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(
        from_attributes=True,
    )


class UserResponse(UserInDBBase):
    """Model for user returned to client (excludes sensitive fields)."""
    pass


class UserInDB(UserInDBBase):
    """Model for user stored in DB."""
    pass


__all__ = [
    "TenantBase",
    "TenantCreate",
    "TenantUpdate",
    "TenantInDBBase",
    "TenantResponse",
    "TenantInDB",
    "UserBase",
    "UserCreate",
    "UserUpdate",
    "UserInDBBase",
    "UserResponse",
    "UserInDB",
]
