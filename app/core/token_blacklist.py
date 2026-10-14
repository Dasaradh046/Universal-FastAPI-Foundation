"""
Token blacklist — tracks revoked JWT IDs (jti) for logout / rotation.

In production this should be backed by Redis with a TTL matching the
token's expiry. For the foundation, an in-process dict is provided as a
default that works for single-process deployments and is easily swappable.
"""

from __future__ import annotations

from datetime import UTC, datetime

# In-memory store: jti -> expiry timestamp (seconds since epoch)
_REVOCATIONS: dict[str, int] = {}


def revoke_token(jti: str, exp: int) -> None:
    """Blacklist a token's jti until its natural expiry."""
    _REVOCATIONS[jti] = exp


def is_token_revoked(jti: str) -> bool:
    """Check if a token's jti is blacklisted and not yet expired."""
    exp = _REVOCATIONS.get(jti)
    if exp is None:
        return False
    if int(datetime.now(UTC).timestamp()) > exp:
        _REVOCATIONS.pop(jti, None)
        return False
    return True


def revoke_all_for_user(user_id: str) -> int:
    """Revoke all tokens for a user (best-effort sweep).

    In-memory implementation is a no-op; production should use Redis SCAN
    by user-key prefix. Returns the number revoked (always 0 here).
    """
    # Placeholder — Redis-backed implementation would go here
    return 0


__all__ = ["revoke_token", "is_token_revoked", "revoke_all_for_user"]
