"""
Domain events for the auth module.
"""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID
from datetime import datetime


@dataclass
class UserLoggedIn:
    """Event raised when a user logs in."""

    user_id: UUID
    tenant_id: UUID
    ip_address: str | None
    user_agent: str | None
    mfa_used: bool
    created_at: datetime


@dataclass
class UserLoggedOut:
    """Event raised when a user logs out."""

    user_id: UUID
    tenant_id: UUID
    session_id: UUID | None
    revoked_all: bool
    created_at: datetime


@dataclass
class PasswordChanged:
    """Event raised when a user changes their password."""

    user_id: UUID
    tenant_id: UUID
    ip_address: str | None
    created_at: datetime


@dataclass
class PasswordResetRequested:
    """Event raised when a password reset is requested."""

    user_id: UUID
    tenant_id: UUID
    ip_address: str | None
    created_at: datetime


@dataclass
class PasswordResetCompleted:
    """Event raised when a password reset is completed."""

    user_id: UUID
    tenant_id: UUID
    ip_address: str | None
    created_at: datetime


@dataclass
class MfaEnabled:
    """Event raised when 2FA is enabled."""

    user_id: UUID
    tenant_id: UUID
    created_at: datetime


@dataclass
class MfaDisabled:
    """Event raised when 2FA is disabled."""

    user_id: UUID
    tenant_id: UUID
    created_at: datetime


@dataclass
class SessionRevoked:
    """Event raised when a device session is revoked."""

    session_id: UUID
    user_id: UUID
    tenant_id: UUID
    revoked_by_user_id: UUID | None
    created_at: datetime


__all__ = [
    "UserLoggedIn",
    "UserLoggedOut",
    "PasswordChanged",
    "PasswordResetRequested",
    "PasswordResetCompleted",
    "MfaEnabled",
    "MfaDisabled",
    "SessionRevoked",
]
