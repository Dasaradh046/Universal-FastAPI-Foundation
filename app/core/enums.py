"""
Shared enums for the application.
"""

from __future__ import annotations

import enum


class Role(str, enum.Enum):
    """User roles for authentication and authorization.

    Two families are defined:

    * **Platform / control-plane roles** â€” operators of the platform itself
    * **Tenant roles** â€” members of a customer organization
    """

    # ---- Platform roles ----
    PLATFORM_OWNER = "platform_owner"
    PLATFORM_ADMIN = "platform_admin"
    PRODUCT_ADMIN = "product_admin"
    BILLING_ADMIN = "billing_admin"
    SECURITY_ADMIN = "security_admin"
    SUPPORT_ADMIN = "support_admin"
    PLATFORM_AUDITOR = "platform_auditor"

    # ---- Tenant roles ----
    TENANT_ADMIN = "tenant_admin"
    HR_ADMIN = "hr_admin"
    FINANCE_ADMIN = "finance_admin"
    IT_ADMIN = "it_admin"
    PAYROLL_ADMIN = "payroll_admin"
    COMPLIANCE_ADMIN = "compliance_admin"
    TENANT_USER = "tenant_user"
    MANAGER = "manager"
    EXECUTIVE = "executive"
    EMPLOYEE = "employee"
    TENANT_AUDITOR = "tenant_auditor"

    def __str__(self) -> str:
        return self.value


class AuditAction(str, enum.Enum):
    """Audit log action types."""

    CREATE = "create"
    READ = "read"
    UPDATE = "update"
    DELETE = "delete"
    AUTH_LOGIN = "auth_login"
    AUTH_LOGOUT = "auth_logout"
    AUTH_FAILED = "auth_failed"
    AUTH_PASSWORD_CHANGE = "auth_password_change"
    STATUS_TRANSITION = "status_transition"
    SECURITY_EVENT = "security_event"
    SYSTEM = "system"


class TenantStatus(str, enum.Enum):
    """Lifecycle states for a tenant."""

    ACTIVE = "ACTIVE"
    TRIAL = "TRIAL"
    SUSPENDED = "SUSPENDED"
    ARCHIVED = "ARCHIVED"


__all__ = [
    "Role",
    "AuditAction",
    "TenantStatus",
]
