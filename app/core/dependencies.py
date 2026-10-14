"""
FastAPI dependencies — auth context and permission guards.

Provides the ``CurrentUser`` type used across auth services, plus the
FastAPI ``Depends``-compatible ``get_current_user`` / role / permission
guards consumed by route handlers.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Annotated, Any
from uuid import UUID

from fastapi import Depends, HTTPException, Request, status

from app.core.config import settings
from app.core.enums import Role
from app.core.exceptions import AuthenticationError, PermissionError
from app.core.security import decode_token, is_token_revoked
from app.core.permissions import ROLE_PERMISSIONS, get_permissions_for_role
from app.core.role_aliases import normalize_role

# Token retrieval helper ------------------------------------------------------ #


def _extract_token(request: Request) -> str | None:
    """Pull a bearer token from the Authorization header or a cookie."""
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        return auth_header[len("Bearer ") :].strip()

    cookie_name = settings.COOKIE_ACCESS_NAME
    cookie_token = request.cookies.get(cookie_name)
    if cookie_token:
        return cookie_token
    return None


# AuthContext ---------------------------------------------------------------- #


@dataclass
class CurrentUser:
    """Authenticated principal extracted from a validated access token."""

    id: UUID
    email: str
    role: str
    tenant_id: UUID
    session_id: UUID | None = None
    permissions: list[str] = None  # type: ignore[assignment]
    effective_roles: list[str] = None  # type: ignore[assignment]
    is_super_admin: bool = False
    is_platform_admin: bool = False
    mfa_enrollment_required: bool = False
    must_change_password: bool = False

    def has_permission(self, permission: str) -> bool:
        """True if this user has ``permission``.

        The wildcard ``"*"`` grants everything; ``"*.own"`` grants any own-scope
        action on any resource (used for self-service profile edits).
        """
        if not self.permissions:
            return False
        if "*" in self.permissions or permission == "*":
            return True
        if permission.endswith(".own") and "profile.view.own" in self.permissions:
            return True
        return permission in self.permissions

    def has_any_permission(self, *perms: str) -> bool:
        return any(self.has_permission(p) for p in perms)

    def has_role(self, *role_names: str) -> bool:
        """True if the user holds any of the given roles (alias-normalized)."""
        if self.is_super_admin:
            return True
        normalized = {normalize_role(r) for r in role_names}
        return bool(normalized.intersection(set(self.effective_roles)))

    def has_any_role(self, *role_names: str) -> bool:
        return self.has_role(*role_names)


def _token_to_current_user(payload: dict[str, Any]) -> CurrentUser:
    """Build a :class:`CurrentUser` from a decoded JWT payload."""
    from uuid import UUID as _UUID

    permissions: list[str] = payload.get("permissions", [])
    roles: list[str] = payload.get("roles", []) or [payload.get("role", "")]
    sid = payload.get("sid")
    session_id = _UUID(sid) if sid else None

    role = payload.get("role", "")
    normalized_role = normalize_role(role)
    is_super_admin = normalized_role == Role.PLATFORM_OWNER.value
    is_platform_admin = normalized_role in {
        Role.PLATFORM_ADMIN.value,
        Role.PLATFORM_OWNER.value,
    }

    # If the token already carries permissions, use them; otherwise derive from roles.
    if not permissions:
        permissions = AuthService_permissions(roles)

    return CurrentUser(
        id=_UUID(payload["sub"]),
        email=payload.get("email", ""),
        role=role,
        tenant_id=_UUID(payload["tenant_id"]),
        session_id=session_id,
        permissions=permissions,
        effective_roles=roles,
        is_super_admin=is_super_admin,
        is_platform_admin=is_platform_admin,
        mfa_enrollment_required=bool(payload.get("mfa_enrollment_required", False)),
        must_change_password=bool(payload.get("must_change_password", False)),
    )


def AuthService_permissions(roles: list[str]) -> list[str]:
    """Compute the union of permissions for a list of role codes."""
    normalized = [normalize_role(r) for r in roles if r]
    if Role.PLATFORM_OWNER.value in normalized:
        return ["*"]
    perms: set[str] = set()
    for r in normalized:
        perms |= ROLE_PERMISSIONS.get(r, set())
    return sorted(perms)


async def get_current_user(request: Request) -> CurrentUser:
    """Resolve the authenticated user from the request's bearer token."""
    token = _extract_token(request)
    if not token:
        raise AuthenticationError("Not authenticated — missing token")

    payload = decode_token(token)
    if not payload:
        raise AuthenticationError("Invalid or expired token")

    if payload.get("type") != "access":
        raise AuthenticationError("Expected an access token")

    jti = payload.get("jti")
    if jti and is_token_revoked(jti):
        raise AuthenticationError("Session has been revoked — please sign in again")

    try:
        return _token_to_current_user(payload)
    except (KeyError, ValueError, TypeError):
        raise AuthenticationError("Invalid or expired token")


async def get_current_active_user(
    user: Annotated[CurrentUser, Depends(get_current_user)],
) -> CurrentUser:
    """Shortcut that additionally verifies the account is active."""
    if not user:
        raise AuthenticationError("Not authenticated")
    return user


def require_permission(*permissions: str):
    """Dependency factory: require one-or-more of the given permissions.

    A user with the ``"*"`` wildcard (platform_owner) auto-passes.
    """

    def _checker(user: Annotated[CurrentUser, Depends(get_current_user)]) -> CurrentUser:
        for perm in permissions:
            if user.has_permission(perm):
                return user
        raise PermissionError(
            f"Insufficient permissions — requires one of: {', '.join(permissions)}"
        )

    return _checker


def require_role(*allowed_roles: str):
    """Dependency factory: require one of the given roles."""

    def _checker(user: Annotated[CurrentUser, Depends(get_current_user)]) -> CurrentUser:
        if user.has_role(*allowed_roles):
            return user
        raise PermissionError(
            f"Requires role: {', '.join(allowed_roles)} (current: {user.role})"
        )

    return _checker


def require_super_admin(
    user: Annotated[CurrentUser, Depends(get_current_user)],
) -> CurrentUser:
    """Dependency: require a platform_owner or is_super_admin flag."""
    if not user.is_super_admin:
        raise PermissionError("Platform owner privileges required")
    return user


def require_platform_admin(
    user: Annotated[CurrentUser, Depends(get_current_user)],
) -> CurrentUser:
    """Dependency: require a platform_admin or above."""
    if not user.is_platform_admin:
        raise PermissionError("Platform admin privileges required")
    return user


def require_tenant_admin(
    user: Annotated[CurrentUser, Depends(get_current_user)],
) -> CurrentUser:
    """Dependency: require a tenant_admin role or above."""
    if user.is_super_admin or user.is_platform_admin:
        return user
    if user.has_role(Role.TENANT_ADMIN.value):
        return user
    raise PermissionError("Tenant admin privileges required")


__all__ = [
    "CurrentUser",
    "get_current_user",
    "get_current_active_user",
    "require_permission",
    "require_role",
    "require_super_admin",
    "require_platform_admin",
    "require_tenant_admin",
]
