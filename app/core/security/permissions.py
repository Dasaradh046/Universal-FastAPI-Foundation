"""
Core permissions module for Universal FastAPI Foundation.

Provides the Permission class for defining module permissions,
ROLE_PERMISSIONS dictionary mapping roles to permissions,
and utility functions for permission checking.
"""

from __future__ import annotations

from typing import Any, Dict, Set, TypedDict, cast, Optional
from enum import Enum

from pydantic import BaseModel, Field


class Permission(BaseModel):
    """Represents a granular permission for access control.
    
    Attributes:
        code: Machine-readable permission code (e.g., 'employees.create')
        name: Human-readable permission name
        description: Optional description of the permission
        module: Optional module name this permission belongs to
        action: Optional action this permission allows
    """
    code: str = Field(..., description="Machine-readable permission code")
    name: str = Field(..., description="Human-readable permission name")
    description: Optional[str] = Field(None, description="Optional description")
    module: Optional[str] = Field(None, description="Optional module name")
    action: Optional[str] = Field(None, description="Optional action")

    model_config = {
        "validate_assignment": True,
        "protected_namespaces": (),
    }


# Role-based permission mappings
# Each role code maps to a set of permission codes that the role encompasses
ROLE_PERMISSIONS: Dict[str, Set[str]] = {
    # Platform roles
    "platform_owner": {
        "*",
    },
    "platform_admin": {
        "users.read",
        "users.write",
        "users.delete",
        "tenants.read",
        "tenants.write",
        "tenants.delete",
        "*",
    },
    "product_admin": {
        "users.read",
        "users.write",
        "tenants.read",
    },
    "billing_admin": {
        "payments.read",
        "payments.write",
    },
    "security_admin": {
        "users.read",
        "users.write",
        "audit.read",
    },
    "support_admin": {
        "users.read",
        "users.write",
    },
    "platform_auditor": {
        "audit.read",
        "users.read",
    },
    # Tenant roles
    "tenant_admin": {
        "users.read",
        "users.write",
        "users.delete",
        "tenants.read",
        "tenants.write",
        "tenants.delete",
        "roles.read",
        "roles.write",
        "permissions.read",
    },
    "hr_admin": {
        "users.read",
        "users.write",
        "employees.read",
        "employees.write",
    },
    "finance_admin": {
        "payments.read",
        "payments.write",
        "invoices.read",
        "invoices.write",
    },
    "it_admin": {
        "users.read",
        "users.write",
        "system.read",
        "system.write",
    },
    "payroll_admin": {
        "payroll.read",
        "payroll.write",
        "employees.read",
    },
    "compliance_admin": {
        "audit.read",
        "reports.read",
    },
    "tenant_user": {
        "users.read",
        "profile.read",
    },
    "manager": {
        "users.read",
        "users.write",
        "employees.read",
        "employees.write",
    },
    "executive": {
        "users.read",
        "users.write",
        "reports.read",
        "analytics.read",
    },
    "employee": {
        "users.read",
        "profile.read",
    },
    "tenant_auditor": {
        "audit.read",
        "users.read",
    },
}


class RolePermissions(TypedDict):
    """Typed dictionary for role-permission mappings."""
    code: str
    permissions: Set[str]


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


def get_permissions_for_role(role_code: str) -> Set[str]:
    """Get the set of permission codes for a given role.
    
    Args:
        role_code: The role code to look up permissions for.
        
    Returns:
        A set of permission codes, or an empty set if the role is not found.
    """
    return ROLE_PERMISSIONS.get(role_code, set())


def has_permission(user_role: str | None, permission_code: str) -> bool:
    """Check if a role has a specific permission.
    
    Args:
        user_role: The role code of the user.
        permission_code: The permission code to check for.
        
    Returns:
        True if the role has the permission, False otherwise.
    """
    if user_role is None or user_role == "*":
        return True
    perms = ROLE_PERMISSIONS.get(user_role, set())
    return permission_code in perms


def has_any_permission(user_role: str | None, permission_codes: list[str]) -> bool:
    """Check if a role has any of the given permissions.
    
    Args:
        user_role: The role code of the user.
        permission_codes: List of permission codes to check for.
        
    Returns:
        True if the role has any of the permissions, False otherwise.
    """
    if user_role is None or user_role == "*":
        return True
    perms = ROLE_PERMISSIONS.get(user_role, set())
    return any(code in perms for code in permission_codes)


def get_role_from_token(token: str) -> str | None:
    """Extract the role from a JWT token.
    
    Args:
        token: The JWT token string.
        
    Returns:
        The role code extracted from the token, or None if not found.
    """
    # In a real implementation, this would decode the JWT and extract the role
    # For now, return None as placeholder
    return None


def get_user_id_from_token(token: str) -> str | None:
    """Extract the user ID from a JWT token.
    
    Args:
        token: The JWT token string.
        
    Returns:
        The user ID extracted from the token, or None if not found.
    """
    # In a real implementation, this would decode the JWT and extract the user ID
    # For now, return None as placeholder
    return None


def get_tenant_id_from_token(token: str) -> str | None:
    """Extract the tenant ID from a JWT token.
    
    Args:
        token: The JWT token string.
        
    Returns:
        The tenant ID extracted from the token, or None if not found.
    """
    # In a real implementation, this would decode the JWT and extract the tenant ID
    # For now, return None as placeholder
    return None
