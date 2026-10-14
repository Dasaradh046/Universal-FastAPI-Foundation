"""
Auth request schemas.
"""

from __future__ import annotations

from pydantic import BaseModel, EmailStr, Field


class AdminPasswordResetRequest(BaseModel):
    """POST /users/{user_id}/reset-password body."""

    password: str | None = Field(
        default=None,
        min_length=8,
        max_length=128,
        description=(
            "Optional password to set. Omit to let the backend generate a "
            "policy-compliant temporary password (recommended)."
        ),
    )


class PlatformUserUpdate(BaseModel):
    """PATCH /users/{user_id} — only the active flag is editable."""

    is_active: bool | None = None


class UserRoleAssignRequest(BaseModel):
    """POST /users/{user_id}/roles body."""

    role: str = Field(
        min_length=2,
        max_length=64,
        pattern=r"^[a-z][a-z0-9_]*$",
        description="Role code to grant, e.g. 'manager', 'finance_admin'.",
    )


class UserRoleOut(BaseModel):
    """A single role row."""

    id: str
    code: str
    name: str
    is_system: bool


class UserRoleListResponse(BaseModel):
    """GET /users/{user_id}/roles response."""

    user_id: str
    roles: list[UserRoleOut]
    effective_permissions: list[str]


class PlatformUserResponse(BaseModel):
    """A login account as seen from platform admin."""

    id: str
    email: str
    name: str | None = None
    role: str
    roles: list[str] = []
    tenant_id: str
    tenant_name: str | None = None
    is_active: bool = True
    is_super_admin: bool = False
    two_factor_enabled: bool = False
    invitation_pending: bool = False
    is_employee_account: bool = False
    must_change_password: bool = False
    password_expired: bool = False
    password_changed_at: str | None = None
    last_login_at: str | None = None
    employee_id: str | None = None
    created_at: str | None = None


class PlatformUserListResponse(BaseModel):
    """Paginated list of platform accounts."""

    items: list[PlatformUserResponse]
    total: int
    page: int
    page_size: int
    total_pages: int = 0


class PlatformUserSummary(BaseModel):
    """Headline counters for the Users screen."""

    total: int = 0
    platform_admins: int = 0
    tenant_admins: int = 0
    active: int = 0
    inactive: int = 0
    pending_invitations: int = 0
    must_change_password: int = 0


class OneTimePasswordResponse(BaseModel):
    """Outcome of an admin-issued password."""

    user_id: str
    email: str
    temporary_password: str | None = None
    password_generated: bool = False
    must_change_password: bool = True
    message: str = ""


__all__ = [
    "AdminPasswordResetRequest",
    "PlatformUserUpdate",
    "UserRoleAssignRequest",
    "UserRoleOut",
    "UserRoleListResponse",
    "PlatformUserResponse",
    "PlatformUserListResponse",
    "PlatformUserSummary",
    "OneTimePasswordResponse",
]
