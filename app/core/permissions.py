"""
Permissions bridge — re-exports permission utilities from ``app.core.security.permissions``.

This module exists as a compatibility layer so modules can import
``from app.core.permissions import ...`` without being tightly coupled
to the security sub-package's internal layout.
"""
from __future__ import annotations

from app.core.security.permissions import (
    Permission,
    ROLE_PERMISSIONS,
    get_permissions_for_role,
    has_permission,
    has_any_permission,
    get_role_from_token,
    get_user_id_from_token,
    get_tenant_id_from_token,
    RolePermissions,
)

__all__ = [
    "Permission",
    "ROLE_PERMISSIONS",
    "get_permissions_for_role",
    "has_permission",
    "has_any_permission",
    "get_role_from_token",
    "get_user_id_from_token",
    "get_tenant_id_from_token",
    "RolePermissions",
]
