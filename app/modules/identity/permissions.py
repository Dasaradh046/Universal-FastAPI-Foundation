"""
Permissions for the identity module.
"""
from __future__ import annotations

from app.core.permissions import Permission

# Tenant permissions
TENANT_READ = Permission(
    code="tenant:read",
    name="Read Tenants",
    description="View tenant information",
    module="identity",
)

TENANT_WRITE = Permission(
    code="tenant:write",
    name="Write Tenants",
    description="Create, update, delete tenants",
    module="identity",
)

TENANT_DELETE = Permission(
    code="tenant:delete",
    name="Delete Tenants",
    description="Delete tenants",
    module="identity",
)


# User permissions
USER_READ = Permission(
    code="user:read",
    name="Read Users",
    description="View user information",
    module="identity",
)

USER_WRITE = Permission(
    code="user:write",
    name="Write Users",
    description="Create, update, delete users",
    module="identity",
)

USER_DELETE = Permission(
    code="user:delete",
    name="Delete Users",
    description="Delete users",
    module="identity",
)


__all__ = [
    "TENANT_READ",
    "TENANT_WRITE",
    "TENANT_DELETE",
    "USER_READ",
    "USER_WRITE",
    "USER_DELETE",
]
