"""
Domain events for the identity module.
"""
from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID
from datetime import datetime


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


__all__ = [
    "TenantCreated",
    "TenantUpdated",
    "TenantDeleted",
    "UserCreated",
    "UserUpdated",
    "UserDeleted",
]
