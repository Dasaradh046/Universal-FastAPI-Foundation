"""
Permissions for the audit module.
"""

from __future__ import annotations

from app.core.permissions import Permission

AUDIT_READ = Permission(
    code="audit:read",
    name="Read Audit Logs",
    description="View audit log entries",
    module="audit",
    action=None,
)

AUDIT_EXPORT = Permission(
    code="audit:export",
    name="Export Audit Logs",
    description="Export audit logs for compliance",
    module="audit",
    action=None,
)

__all__ = [
    "AUDIT_READ",
    "AUDIT_EXPORT",
]
