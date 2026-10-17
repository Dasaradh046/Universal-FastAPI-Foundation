"""
Permissions for the tenant module.
"""

from __future__ import annotations

from app.core.permissions import Permission

TENANT_CONTEXT_READ = Permission(
    code="tenant:context:read",
    name="Read Tenant Context",
    description="View current tenant context information",
    module="tenant",
)

TENANT_CONTEXT_WRITE = Permission(
    code="tenant:context:write",
    name="Write Tenant Context",
    description="Update tenant context configuration",
    module="tenant",
)

TENANT_SWITCH = Permission(
    code="tenant:switch",
    name="Switch Tenant",
    description="Switch tenant context",
    module="tenant",
)

__all__ = [
    "TENANT_CONTEXT_READ",
    "TENANT_CONTEXT_WRITE",
    "TENANT_SWITCH",
]
