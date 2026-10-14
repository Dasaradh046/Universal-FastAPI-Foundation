"""
Role aliases and normalization for backward compatibility.
"""

from __future__ import annotations

from app.core.enums import Role

ROLE_ALIASES: dict[str, str] = {
    "super_admin": Role.PLATFORM_OWNER.value,
    "superadmin": Role.PLATFORM_OWNER.value,
    "admin": Role.PLATFORM_ADMIN.value,
    "owner": Role.PLATFORM_OWNER.value,
    "hr": Role.HR_ADMIN.value,
    "finance": Role.FINANCE_ADMIN.value,
    "manager": Role.MANAGER.value,
    "user": Role.TENANT_USER.value,
}


def normalize_role(role: str) -> str:
    """Normalize a role string to its canonical value.

    Handles legacy role values that may appear in existing JWTs or DB rows,
    ensuring consistent permission checks.
    """
    if not role:
        return ""
    lowered = role.lower()
    return ROLE_ALIASES.get(lowered, lowered)


def normalize_roles(roles: list[str]) -> list[str]:
    """Normalize a list of role strings."""
    return [normalize_role(r) for r in roles if r]


__all__ = ["ROLE_ALIASES", "normalize_role", "normalize_roles"]
