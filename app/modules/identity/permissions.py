"""
Permissions for the identity module.
"""
from __future__ import annotations

from app.core.security.permissions import Permission

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


# Role permissions
ROLE_READ = Permission(
    code="role:read",
    name="Read Roles",
    description="View role information",
    module="identity",
)

ROLE_WRITE = Permission(
    code="role:write",
    name="Write Roles",
    description="Create, update roles",
    module="identity",
)

ROLE_DELETE = Permission(
    code="role:delete",
    name="Delete Roles",
    description="Delete roles",
    module="identity",
)

ROLE_ASSIGN = Permission(
    code="role:assign",
    name="Assign Roles",
    description="Assign and revoke roles from users",
    module="identity",
)


__all__ = [
    "ROLE_ASSIGN",
    "ROLE_DELETE",
    "ROLE_READ",
    "ROLE_WRITE",
    "TENANT_DELETE",
    "TENANT_READ",
    "TENANT_WRITE",
    "USER_DELETE",
    "USER_READ",
    "USER_WRITE",
]
