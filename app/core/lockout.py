"""
Account lockout and rate limiting utilities for authentication flows.

Provides progressive lockout after repeated failed attempts:
- Login: 5 attempts per 15 min per client IP (P0 -100)
- MFA: 10 attempts per 15 min per client IP (P0 -99)

Lockouts are per-account + per-IP, tracked in-memory (replace with Redis
in production for multi-instance deployments).
"""

from __future__ import annotations

import time
from collections import defaultdict
from dataclasses import dataclass
from uuid import UUID

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

# In-memory lockout store: (tenant_id, user_id, ip) -> list of failure timestamps
_login_failures: dict[tuple[UUID | None, UUID | None, str | None], list[float]] = defaultdict(list)
_mfa_failures: dict[tuple[UUID | None, UUID | None, str | None], list[float]] = defaultdict(list)

# Track per-account lockouts to prevent brute-force on known accounts
_account_lockouts: dict[UUID, float] = {}  # user_id -> lockout_until timestamp


@dataclass
class LockoutState:
    """State of a login attempt under the lockout policy."""

    remaining: int  # attempts remaining before lockout
    locked: bool    # whether the account/IP is currently locked
    lockout_seconds: float  # seconds until lockout expires (0 if not locked)


async def check_login_lockout(
    tenant_id: UUID | None,
    user_id: UUID | None,
    ip_address: str | None,
) -> None:
    """Check and enforce login lockout (P0 -100).

    Raises ``AuthenticationError`` if the account or IP is locked.
    """
    from app.core.exceptions import AuthenticationError

    now = time.time()
    window = settings.LOGIN_RATE_LIMIT_WINDOW
    max_attempts = settings.LOGIN_RATE_LIMIT_REQUESTS

    # Check account-level lockout
    if user_id is not None:
        lockout_until = _account_lockouts.get(user_id)
        if lockout_until and lockout_until > now:
            locked_for = int(lockout_until - now)
            logger.warning(
                "Login blocked (account locked): user=%s ip=%s locked_for=%ss",
                user_id, ip_address, locked_for,
            )
            raise AuthenticationError(
                "Too many failed login attempts. Please try again later.",
                error_code="account_locked",
            )

    # Check IP-based attempts
    key = (tenant_id, user_id, ip_address)
    failures = _login_failures[key]
    # Prune old failures outside the window
    failures[:] = [t for t in failures if now - t < window]
    if len(failures) >= max_attempts:
        # Lock the account if we know the user_id
        if user_id is not None:
            _account_lockouts[user_id] = now + window
        logger.warning(
            "Login blocked (IP rate-limited): user=%s ip=%s",
            user_id, ip_address,
        )
        raise AuthenticationError(
            "Too many failed login attempts. Please try again later.",
            error_code="rate_limited",
        )


async def record_failed_login(
    tenant_id: UUID | None,
    user_id: UUID | None,
    ip_address: str | None,
) -> None:
    """Record a failed login attempt."""
    now = time.time()
    key = (tenant_id, user_id, ip_address)
    _login_failures[key].append(now)
    # Prune old entries
    window = settings.LOGIN_RATE_LIMIT_WINDOW
    _login_failures[key] = [t for t in _login_failures[key] if now - t < window]


async def reset_login_failures(
    tenant_id: UUID | None,
    user_id: UUID | None,
    ip_address: str | None,
) -> None:
    """Reset failure counters after successful login."""
    key = (tenant_id, user_id, ip_address)
    _login_failures.pop(key, None)
    if user_id is not None:
        _account_lockouts.pop(user_id, None)


async def check_mfa_lockout(
    tenant_id: UUID | None,
    user_id: UUID | None,
    ip_address: str | None,
) -> None:
    """Check and enforce MFA lockout (P0 -99)."""
    from app.core.exceptions import AuthenticationError

    now = time.time()
    window = settings.MFA_RATE_LIMIT_WINDOW
    max_attempts = settings.MFA_RATE_LIMIT_REQUESTS

    key = (tenant_id, user_id, ip_address)
    failures = _mfa_failures[key]
    failures[:] = [t for t in failures if now - t < window]
    if len(failures) >= max_attempts:
        logger.warning(
            "MFA blocked (rate-limited): user=%s ip=%s",
            user_id, ip_address,
        )
        raise AuthenticationError(
            "Too many failed verification attempts. Please try again later.",
            error_code="mfa_locked",
        )


async def record_failed_mfa(
    tenant_id: UUID | None,
    user_id: UUID | None,
    ip_address: str | None,
) -> None:
    """Record a failed MFA attempt."""
    now = time.time()
    key = (tenant_id, user_id, ip_address)
    _mfa_failures[key].append(now)
    window = settings.MFA_RATE_LIMIT_WINDOW
    _mfa_failures[key] = [t for t in _mfa_failures[key] if now - t < window]


async def reset_mfa_failures(
    tenant_id: UUID | None,
    user_id: UUID | None,
    ip_address: str | None,
) -> None:
    """Reset MFA failure counters after successful verification."""
    key = (tenant_id, user_id, ip_address)
    _mfa_failures.pop(key, None)


def unlock_account(tenant_id: UUID, user_id: UUID) -> None:
    """Admin override: unlock an account's lockout."""
    _account_lockouts.pop(user_id, None)
    logger.info("Account unlocked: tenant=%s user=%s", tenant_id, user_id)


def unlock_mfa(tenant_id: UUID, user_id: UUID) -> None:
    """Admin override: unlock an account's MFA lockout."""
    key = (tenant_id, user_id, None)
    _mfa_failures.pop(key, None)
    logger.info("MFA unlocked: tenant=%s user=%s", tenant_id, user_id)


__all__ = [
    "check_login_lockout",
    "record_failed_login",
    "reset_login_failures",
    "check_mfa_lockout",
    "record_failed_mfa",
    "reset_mfa_failures",
    "unlock_account",
    "unlock_mfa",
]
