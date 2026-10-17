"""
Dependencies bridge — re-exports auth dependencies from ``app.core.security``.

This module exists as a compatibility layer so modules can import
``from app.core.dependencies import ...`` without being tightly coupled
to the security sub-package's internal layout.
"""
from __future__ import annotations

from app.core.security import (
    CurrentUser,
    get_current_user,
    get_current_active_user,
    require_permission,
    require_role,
    require_super_admin,
    require_platform_admin,
    require_tenant_admin,
)

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
