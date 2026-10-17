"""
Tenant schemas for the identity module.

Follows the application-wide ResponseEnvelope pattern for consistent API responses.
"""
from __future__ import annotations

from datetime import datetime
from typing import TypeVar
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models.enums import TenantStatus
from app.schemas.common import ResponseEnvelope

T = TypeVar("T")


class TenantBase(BaseModel):
    """Base tenant model — write-only fields that may be set on create/update."""

    name: str = Field(..., min_length=1, max_length=160)
    slug: str = Field(
        ...,
        min_length=2,
        max_length=80,
        pattern=r"^[a-z0-9][a-z0-9\-_]*$",
        description="URL-safe unique identifier (lowercase letters, digits, hyphens, underscores)",
    )
    plan: str | None = Field(None, max_length=32)
    is_platform: bool | None = Field(None, description="Whether this is a platform-level tenant")

    # Encrypted sensitive fields (write-only — plaintext accepted, encrypted on save)
    billing_email: EmailStr | None = Field(None, max_length=255)
    billing_address: str | None = Field(None, max_length=500)
    tax_id: str | None = Field(None, max_length=50)
    primary_contact_phone: str | None = Field(None, max_length=20)

    # Settings
    timezone: str | None = Field(None, max_length=64, description="IANA timezone name")
    locale: str | None = Field(None, max_length=16, description="Locale code, e.g. en-US")
    password_policy_id: UUID | None = Field(None, description="ID of the password policy to apply")
    status: TenantStatus | None = Field(None, description="Tenant lifecycle status")

    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
        use_enum_values=True,
    )


class TenantCreate(TenantBase):
    """Model for creating a new tenant."""

    status: TenantStatus = Field(
        default=TenantStatus.ACTIVE,
        description="Initial tenant status",
    )

    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
        use_enum_values=True,
    )


class TenantUpdate(BaseModel):
    """Model for updating a tenant — all fields optional."""

    name: str | None = Field(None, min_length=1, max_length=160)
    slug: str | None = Field(
        None,
        min_length=2,
        max_length=80,
        pattern=r"^[a-z0-9][a-z0-9\-_]*$",
    )
    plan: str | None = Field(None, max_length=32)
    is_platform: bool | None = None
    billing_email: EmailStr | None = Field(None, max_length=255)
    billing_address: str | None = Field(None, max_length=500)
    tax_id: str | None = Field(None, max_length=50)
    primary_contact_phone: str | None = Field(None, max_length=20)
    timezone: str | None = Field(None, max_length=64)
    locale: str | None = Field(None, max_length=16)
    password_policy_id: UUID | None = None

    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
        use_enum_values=True,
    )


class TenantStatusUpdate(BaseModel):
    """Model for updating a tenant's lifecycle status."""

    status: TenantStatus = Field(..., description="New tenant status")
    reason: str | None = Field(None, max_length=500, description="Reason for the status change")

    model_config = ConfigDict(str_strip_whitespace=True)


class TenantSettings(BaseModel):
    """Model for updating tenant settings independently of tenant record."""

    timezone: str | None = Field(None, max_length=64)
    locale: str | None = Field(None, max_length=16)
    password_policy_id: UUID | None = None
    plan: str | None = Field(None, max_length=32)

    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
    )


class TenantInDBBase(BaseModel):
    """Base model for tenant data stored in the DB (read path)."""

    id: UUID
    name: str
    slug: str
    status: TenantStatus
    plan: str | None = None
    is_platform: bool = False
    timezone: str
    locale: str
    password_policy_id: UUID | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    # Encrypted fields are decrypted on read by the TypeDecorator
    billing_email: str | None = None
    billing_address: str | None = None
    tax_id: str | None = None
    primary_contact_phone: str | None = None

    model_config = ConfigDict(from_attributes=True, use_enum_values=True)


class TenantResponse(TenantInDBBase):
    """Model for tenant returned to client."""


class TenantInDB(TenantInDBBase):
    """Full tenant model including internal fields."""


class TenantStatsResponse(BaseModel):
    """Aggregate statistics for a tenant."""

    tenant_id: UUID
    total_users: int = 0
    active_users: int = 0
    inactive_users: int = 0
    locked_users: int = 0
    mfa_enabled_users: int = 0
    admin_users: int = 0
    must_change_password: int = 0
    mfa_enrollment_required: int = 0
    created_at: datetime | None = None
    updated_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


# ---- Response envelope specializations ---- #

class TenantResponseEnvelope(ResponseEnvelope[TenantResponse]):
    """Single tenant response envelope."""


class TenantListResponseEnvelope(ResponseEnvelope[list[TenantResponse]]):
    """List of tenants response envelope."""


class TenantStatsResponseEnvelope(ResponseEnvelope[TenantStatsResponse]):
    """Tenant statistics response envelope."""


__all__ = [
    "TenantBase",
    "TenantCreate",
    "TenantInDB",
    "TenantInDBBase",
    "TenantListResponseEnvelope",
    "TenantResponse",
    "TenantResponseEnvelope",
    "TenantSettings",
    "TenantStatsResponse",
    "TenantStatsResponseEnvelope",
    "TenantStatusUpdate",
    "TenantUpdate",
]
