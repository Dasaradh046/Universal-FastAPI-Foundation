"""
Domain events for the identity module.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass
class TenantCreated:
    """Event raised when a tenant is created."""
    tenant_id: UUID
    name: str
    created_at: datetime


@dataclass
class TenantUpdated:
    """Event raised when a tenant is updated."""
    tenant_id: UUID
    name: str
    updated_at: datetime


@dataclass
class TenantStatusChanged:
    """Event raised when a tenant's status changes."""
    tenant_id: UUID
    status: str
    changed_at: datetime


@dataclass
class TenantDeleted:
    """Event raised when a tenant is deleted."""
    tenant_id: UUID
    deleted_at: datetime


@dataclass
class UserCreated:
    """Event raised when a user is created."""
    user_id: UUID
    email: str
    tenant_id: UUID
    created_at: datetime


@dataclass
class UserUpdated:
    """Event raised when a user is updated."""
    user_id: UUID
    email: str
    tenant_id: UUID
    updated_at: datetime


@dataclass
class UserDeleted:
    """Event raised when a user is deleted."""
    user_id: UUID
    email: str
    tenant_id: UUID
    deleted_at: datetime


@dataclass
class UserActivated:
    """Event raised when a user account is activated."""
    user_id: UUID
    tenant_id: UUID
    activated_at: datetime


@dataclass
class UserDeactivated:
    """Event raised when a user account is deactivated."""
    user_id: UUID
    tenant_id: UUID
    deactivated_at: datetime


@dataclass
class UserLocked:
    """Event raised when a user account is locked."""
    user_id: UUID
    tenant_id: UUID
    reason: str | None
    locked_at: datetime


@dataclass
class UserUnlocked:
    """Event raised when a user account is unlocked."""
    user_id: UUID
    tenant_id: UUID
    unlocked_at: datetime


@dataclass
class RoleAssigned:
    """Event raised when an additional role is assigned to a user."""
    user_id: UUID
    role_id: UUID
    role_code: str
    tenant_id: UUID
    assigned_at: datetime


@dataclass
class RoleRevoked:
    """Event raised when an additional role is revoked from a user."""
    user_id: UUID
    role_id: UUID
    role_code: str
    tenant_id: UUID
    revoked_at: datetime


@dataclass
class RoleCreated:
    """Event raised when a role is created."""
    role_id: UUID
    role_code: str
    tenant_id: UUID
    created_at: datetime


@dataclass
class RoleUpdated:
    """Event raised when a role is updated."""
    role_id: UUID
    role_code: str
    tenant_id: UUID
    updated_at: datetime


@dataclass
class RoleDeleted:
    """Event raised when a role is deleted."""
    role_id: UUID
    role_code: str
    tenant_id: UUID
    deleted_at: datetime


@dataclass
class PasswordReset:
    """Event raised when a user's password is reset by an administrator."""
    user_id: UUID
    tenant_id: UUID
    reset_by: UUID | None
    created_at: datetime


__all__ = [
    "PasswordReset",
    "RoleAssigned",
    "RoleCreated",
    "RoleDeleted",
    "RoleRevoked",
    "RoleUpdated",
    "TenantCreated",
    "TenantDeleted",
    "TenantStatusChanged",
    "TenantUpdated",
    "UserActivated",
    "UserCreated",
    "UserDeactivated",
    "UserDeleted",
    "UserLocked",
    "UserUnlocked",
    "UserUpdated",
]
