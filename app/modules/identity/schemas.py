"""
Pydantic schemas for the identity module.

Follows the application-wide ResponseEnvelope pattern for consistent API responses.
Includes tenant and user management schemas.
"""

from __future__ import annotations

from pydantic import BaseModel, Field, ConfigDict, EmailStr
from typing import Optional, Generic, TypeVar
from datetime import datetime
from uuid import UUID

from app.schemas.common import ResponseEnvelope

T = TypeVar("T")


# =============================================================================
# Tenant Schemas
# =============================================================================

class TenantBase(BaseModel):
    """Base tenant model."""
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=1000)
    # Encrypted sensitive fields (write-only in create/update)
    billing_email: Optional[str] = Field(None, max_length=255)
    billing_address: Optional[str] = Field(None, max_length=500)
    tax_id: Optional[str] = Field(None, max_length=50)
    primary_contact_phone: Optional[str] = Field(None, max_length=20)

    # Settings
    timezone: Optional[str] = Field(None, max_length=64)
    locale: Optional[str] = Field(None, max_length=16)
    password_policy_id: Optional[UUID] = Field(None)

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
    billing_email: Optional[str] = Field(None, max_length=255)
    billing_address: Optional[str] = Field(None, max_length=500)
    tax_id: Optional[str] = Field(None, max_length=50)
    primary_contact_phone: Optional[str] = Field(None, max_length=20)
    timezone: Optional[str] = Field(None, max_length=64)
    locale: Optional[str] = Field(None, max_length=16)
    password_policy_id: Optional[UUID] = Field(None)
    is_active: Optional[bool] = Field(None)

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

    # Encrypted fields are not included in responses for security
    model_config = ConfigDict(
        from_attributes=True,
    )


class TenantResponse(TenantInDBBase):
    """Model for tenant returned to client."""
    pass


class TenantInDB(TenantInDBBase):
    """Model for tenant stored in DB."""
    pass


# =============================================================================
# User Schemas
# =============================================================================

class UserBase(BaseModel):
    """Base user model."""
    email: EmailStr = Field(..., max_length=255)
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
    email: Optional[EmailStr] = Field(None, max_length=255)
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


# =============================================================================
# Response Envelope Specializations
# =============================================================================

class TenantResponseEnvelope(ResponseEnvelope[TenantResponse]):
    """Single tenant response envelope."""
    pass


class TenantListResponseEnvelope(ResponseEnvelope[list[TenantResponse]]):
    """List of tenants response envelope."""
    pass


class UserResponseEnvelope(ResponseEnvelope[UserResponse]):
    """Single user response envelope."""
    pass


class UserListResponseEnvelope(ResponseEnvelope[list[UserResponse]]):
    """List of users response envelope."""
    pass


__all__ = [
    # Tenant schemas
    "TenantBase",
    "TenantCreate",
    "TenantUpdate",
    "TenantInDBBase",
    "TenantResponse",
    "TenantInDB",
    # User schemas
    "UserBase",
    "UserCreate",
    "UserUpdate",
    "UserInDBBase",
    "UserResponse",
    "UserInDB",
    # Response envelopes
    "TenantResponseEnvelope",
    "TenantListResponseEnvelope",
    "UserResponseEnvelope",
    "UserListResponseEnvelope",
]