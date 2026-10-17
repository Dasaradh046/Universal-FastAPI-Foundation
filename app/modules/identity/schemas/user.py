"""
User schemas for the identity module.

Follows the application-wide ResponseEnvelope pattern for consistent API responses.
The User model lives in ``app.models.user``; these schemas define the API
contract for identity (non-auth) user operations.
"""
from __future__ import annotations

from datetime import datetime
from typing import TypeVar
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models.enums import Role
from app.schemas.common import ResponseEnvelope

T = TypeVar("T")


class UserBase(BaseModel):
    """Base user model — fields that may be set on create/update."""

    email: EmailStr = Field(..., max_length=255)
    name: str | None = Field(None, max_length=160)
    first_name: str | None = Field(None, max_length=80)
    last_name: str | None = Field(None, max_length=80)
    job_title: str | None = Field(None, max_length=120)
    avatar_color: str | None = Field(None, max_length=16)
    employee_id: UUID | None = Field(None)

    # Role & permissions
    role: Role | None = Field(Role.EMPLOYEE, description="Primary role")

    # Account state
    is_active: bool | None = Field(True)
    is_super_admin: bool | None = Field(False)
    is_demo: bool | None = Field(False)

    # Password lifecycle
    must_change_password: bool | None = Field(False)
    mfa_enrollment_required: bool | None = Field(False)

    # PII fields (plaintext in schema → encrypted on save by repository)
    phone: str | None = Field(None, max_length=20)
    address: str | None = Field(None, max_length=500)
    date_of_birth: str | None = Field(None, description="ISO date string, e.g. 1990-01-15")
    government_id: str | None = Field(None, max_length=100)
    emergency_contact: str | None = Field(None, max_length=255)

    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
        use_enum_values=True,
    )


class UserCreate(UserBase):
    """Model for creating a new user.

    ``password`` is optional — when omitted the user is created in
    "pending invitation" state and the auth module's invitation flow
    sets the initial password.
    """

    password: str | None = Field(
        None,
        min_length=8,
        max_length=128,
        description="Optional initial password. Omit for invitation-based creation.",
    )


class UserUpdate(BaseModel):
    """Model for updating a user — all fields optional."""

    email: EmailStr | None = Field(None, max_length=255)
    name: str | None = Field(None, max_length=160)
    first_name: str | None = Field(None, max_length=80)
    last_name: str | None = Field(None, max_length=80)
    job_title: str | None = Field(None, max_length=120)
    avatar_color: str | None = Field(None, max_length=16)
    employee_id: UUID | None = None
    role: Role | None = None
    is_active: bool | None = None
    is_super_admin: bool | None = None
    is_demo: bool | None = None
    must_change_password: bool | None = None
    mfa_enrollment_required: bool | None = None
    password: str | None = Field(None, min_length=8, max_length=128)
    phone: str | None = Field(None, max_length=20)
    address: str | None = Field(None, max_length=500)
    date_of_birth: str | None = None
    government_id: str | None = Field(None, max_length=100)
    emergency_contact: str | None = Field(None, max_length=255)

    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
        use_enum_values=True,
    )


class UserStatusUpdate(BaseModel):
    """Model for updating a user's active status."""

    is_active: bool = Field(..., description="Whether the user account is active")
    reason: str | None = Field(None, max_length=500, description="Reason for the status change")

    model_config = ConfigDict(str_strip_whitespace=True)


class UserPasswordReset(BaseModel):
    """Model for an admin resetting a user's password."""

    password: str | None = Field(
        None,
        min_length=8,
        max_length=128,
        description="Optional new password. Omit to let the backend generate one.",
    )
    must_change_password: bool = Field(
        True,
        description="Force the user to change password on next login",
    )
    send_email: bool = Field(
        True,
        description="Email the new password to the user",
    )

    model_config = ConfigDict(str_strip_whitespace=True)


class UserBulkStatusUpdate(BaseModel):
    """Model for bulk updating user status."""

    user_ids: list[UUID] = Field(..., min_length=1, max_length=1000)
    is_active: bool | None = None
    mfa_enrollment_required: bool | None = None

    model_config = ConfigDict(str_strip_whitespace=True)


class UserInDBBase(BaseModel):
    """Base model for user data stored in DB (read path)."""

    id: UUID
    tenant_id: UUID
    email: str
    email_verified: bool = False
    email_verified_at: datetime | None = None
    name: str | None = None
    first_name: str | None = None
    last_name: str | None = None
    job_title: str | None = None
    avatar_color: str | None = None
    initials: str | None = None
    employee_id: UUID | None = None
    role: str
    is_active: bool = True
    is_super_admin: bool = False
    is_demo: bool = False
    must_change_password: bool = False
    mfa_enrollment_required: bool = False
    two_factor_enabled: bool = False
    two_factor_confirmed_at: datetime | None = None
    last_login_at: datetime | None = None
    last_login_ip: str | None = None
    password_changed_at: datetime | None = None
    failed_login_attempts: int = 0
    last_failed_login_at: datetime | None = None
    locked_out_at: datetime | None = None
    lockout_reason: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    # Computed properties exposed in the response
    is_locked_out: bool = False
    password_expired: bool = False
    password_expires_soon: bool = False
    requires_password_change: bool = False

    # Decrypted PII fields (available on read via TypeDecorator)
    phone: str | None = None
    address: str | None = None
    date_of_birth: str | None = None
    government_id: str | None = None
    emergency_contact: str | None = None

    model_config = ConfigDict(
        from_attributes=True,
        use_enum_values=True,
    )


class UserResponse(UserInDBBase):
    """Model for user returned to client (excludes password_hash and tokens)."""


class UserInDB(UserInDBBase):
    """Full user model including internal fields."""
    password_hash: str | None = None
    password_history_encrypted: str | None = None
    totp_secret_encrypted: str | None = None
    totp_recovery_codes_encrypted: str | None = None

    model_config = ConfigDict(
        from_attributes=True,
        use_enum_values=True,
    )


class UserSessionResponse(BaseModel):
    """A user's active device session."""

    id: UUID
    device: str | None = None
    browser: str | None = None
    location: str | None = None
    ip_address: str | None = None
    is_current: bool = False
    expires_at: datetime | None = None
    created_at: datetime | None = None
    last_active_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class UserRoleAssign(BaseModel):
    """Assign an additional role to a user."""

    role_code: str = Field(
        ...,
        min_length=2,
        max_length=64,
        pattern=r"^[a-z][a-z0-9_\-]*$",
        description="Role code to assign (e.g. 'manager', 'finance_admin')",
    )

    model_config = ConfigDict(str_strip_whitespace=True)


class UserRoleResponse(BaseModel):
    """A role assigned to a user."""

    id: UUID
    code: str
    name: str
    is_system: bool = False
    assigned_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class UserStatsResponse(BaseModel):
    """Aggregate user statistics for a tenant."""

    tenant_id: UUID
    total_users: int = 0
    active_users: int = 0
    inactive_users: int = 0
    locked_out_users: int = 0
    mfa_enabled_users: int = 0
    admin_users: int = 0
    must_change_password: int = 0
    mfa_enrollment_required: int = 0
    by_role: dict[str, int] = Field(default_factory=dict)

    model_config = ConfigDict(from_attributes=True)


# ---- Response envelope specializations ---- #

class UserResponseEnvelope(ResponseEnvelope[UserResponse]):
    """Single user response envelope."""


class UserListResponseEnvelope(ResponseEnvelope[list[UserResponse]]):
    """List of users response envelope."""


class UserStatsResponseEnvelope(ResponseEnvelope[UserStatsResponse]):
    """User statistics response envelope."""


class UserSessionListResponseEnvelope(ResponseEnvelope[list[UserSessionResponse]]):
    """List of user sessions response envelope."""


class UserRoleListResponseEnvelope(ResponseEnvelope[list[UserRoleResponse]]):
    """List of user roles response envelope."""


__all__ = [
    "UserBase",
    "UserBulkStatusUpdate",
    "UserCreate",
    "UserInDB",
    "UserInDBBase",
    "UserListResponseEnvelope",
    "UserPasswordReset",
    "UserResponse",
    "UserResponseEnvelope",
    "UserRoleAssign",
    "UserRoleListResponseEnvelope",
    "UserRoleResponse",
    "UserSessionListResponseEnvelope",
    "UserSessionResponse",
    "UserStatsResponse",
    "UserStatsResponseEnvelope",
    "UserStatusUpdate",
    "UserUpdate",
]
