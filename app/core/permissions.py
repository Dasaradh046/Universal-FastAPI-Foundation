"""
RBAC permission matrix for the Universal FastAPI Foundation.

Permissions use the ``resource.action.scope`` format, shared with the
frontend. Resource names may contain dotted sub-resources.

Actions: view, create, update, delete, approve, export, configure
Scopes: own, team, department, all
"""

from __future__ import annotations

from app.core.role_aliases import normalize_role
from app.core.enums import Role

# Canonical platform permissions published to admin clients
CANONICAL_PLATFORM_PERMISSIONS: tuple[str, ...] = (
    "platform.dashboard.view",
    "platform.tenants.view",
    "platform.tenants.create",
    "platform.tenants.configure",
    "platform.tenants.suspend",
    "platform.tenants.resume",
    "platform.tenants.archive",
    "platform.tenants.restore",
    "platform.tenant_modules.view",
    "platform.tenant_modules.manage",
    "platform.identity.manage",
    "platform.identity.view",
    "platform.identity.create",
    "platform.identity_status.manage",
    "platform.identity_roles.manage",
    "platform.identity_sessions.manage",
    "platform.identity_mfa.manage",
    "platform.security.manage",
    "platform.security_policy.view",
    "platform.security_policy.draft",
    "platform.security_policy.publish",
    "platform.security_event.view",
    "platform.configuration.manage",
    "platform.configuration.view",
    "platform.configuration.draft",
    "platform.configuration.publish",
    "platform.integrations.view",
    "platform.integrations.manage",
    "platform.operations.view",
    "platform.operations.retry",
    "platform.operations.replay",
    "platform.operations.reconcile",
    "platform.operations.quarantine",
    "platform.operations.cancel",
    "platform.operations.requeue",
    "platform.audit.view",
    "platform.audit.export",
    "platform.support_access.view",
    "platform.support_access.request",
    "platform.support_access.approve",
    "platform.support_access.use",
    "platform.support_access.revoke",
)

# Permission format: "resource.action.scope"
# Role -> set of permission strings
ROLE_PERMISSIONS: dict[str, set[str]] = {
    "platform_owner": set(),  # All permissions — checked via is_super_admin flag
    "platform_admin": {
        "platform_identity.manage.all",
        "platform_identity.view.all",
        "platform_identity.create.all",
        "platform_identity_status.manage.all",
        "platform_identity_roles.manage.all",
        "platform_identity_sessions.manage.all",
        "platform_identity_mfa.manage.all",
        "platform_dashboard.view.all",
        "platform_tenants.view.all",
        "platform_tenants.create.all",
        "platform_tenants.configure.all",
        "platform_security.manage.all",
        "platform_security_policy.view.all",
        "platform_security_event.view.all",
        "platform_audit.view.all",
        "profile.view.own",
    },
    "platform_auditor": {
        "platform_dashboard.view.all",
        "platform_tenants.view.all",
        "platform_audit.view.all",
        "platform_identity.view.all",
        "platform_security_policy.view.all",
        "platform_security_event.view.all",
        "profile.view.own",
    },
    "product_admin": {
        "platform_dashboard.view.all",
        "platform_integrations.view.all",
        "platform_integrations.manage.all",
        "platform_configuration.view.all",
        "platform_operations.view.all",
        "profile.view.own",
    },
    "billing_admin": {
        "platform_dashboard.view.all",
        "platform_tenants.view.all",
        "platform_subscriptions.view.all",
        "platform_subscriptions.manage.all",
        "platform_billing.view.all",
        "platform_billing.manage.all",
        "platform_audit.view.all",
        "profile.view.own",
    },
    "support_admin": {
        "platform_dashboard.view.all",
        "platform_tenants.view.all",
        "platform_support.view.all",
        "platform_support.manage.all",
        "platform_support_access.view.all",
        "platform_support_access.request.all",
        "profile.view.own",
    },
    "security_admin": {
        "platform_dashboard.view.all",
        "platform_tenants.view.all",
        "platform_identity.manage.all",
        "platform_identity.view.all",
        "platform_identity.create.all",
        "platform_identity_status.manage.all",
        "platform_identity_roles.manage.all",
        "platform_identity_sessions.manage.all",
        "platform_identity_mfa.manage.all",
        "platform_security.manage.all",
        "platform_security_policy.view.all",
        "platform_security_policy.draft.all",
        "platform_security_policy.publish.all",
        "platform_security_event.view.all",
        "platform_operations.view.all",
        "profile.view.own",
    },
    "support_admin": {
        "platform_dashboard.view.all",
        "platform_tenants.view.all",
        "platform_support.view.all",
        "platform_support_access.view.all",
        "platform_support_access.request.all",
        "platform_support_access.use.all",
        "platform_audit.view.all",
        "profile.view.own",
    },
    "tenant_admin": {
        "profile.view.own",
        "employees.view.all",
        "employees.create.all",
        "employees.update.all",
        "departments.view.all",
        "departments.create.all",
        "departments.update.all",
        "payroll.view.all",
        "payroll.create.all",
        "settings.view.all",
    },
    "hr_admin": {
        "profile.view.own",
        "employees.view.all",
        "employees.create.all",
        "employees.update.all",
        "departments.view.all",
        "departments.create.all",
        "leave_requests.view.all",
        "leave_requests.create.all",
    },
    "finance_admin": {
        "profile.view.own",
        "payroll.view.all",
        "expenses.view.all",
        "expenses.create.all",
    },
    "it_admin": {
        "profile.view.own",
        "it_access.view.all",
        "it_access.create.all",
        "devices.view.all",
    },
    "employee": {
        "profile.view.own",
        "leave_requests.view.own",
        "leave_requests.create.own",
        "expenses.view.own",
        "expenses.create.own",
    },
    "manager": {
        "profile.view.own",
        "employees.view.team",
        "leave_requests.view.team",
        "leave_requests.approve.team",
    },
    "tenant_user": {
        "profile.view.own",
    },
}

# Convenience: map of Role enum values to their permission sets
def get_permissions_for_role(role: str) -> set[str]:
    """Return the permission set for a role, normalizing aliases."""
    normalized = normalize_role(role)
    if normalized == Role.PLATFORM_OWNER.value:
        # platform_owner gets all canonical permissions
        return set(CANONICAL_PLATFORM_PERMISSIONS)
    return ROLE_PERMISSIONS.get(normalized, set())


__all__ = [
    "CANONICAL_PLATFORM_PERMISSIONS",
    "ROLE_PERMISSIONS",
    "get_permissions_for_role",
]
