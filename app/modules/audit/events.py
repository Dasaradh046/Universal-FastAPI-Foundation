"""
Domain events for the audit module.
"""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID
from datetime import datetime


@dataclass
class AuditLogCreated:
    """Event raised when an audit log is created."""

    log_id: UUID
    tenant_id: UUID
    action: str
    resource: str
    created_at: datetime


@dataclass
class AuditLogsExported:
    """Event raised when audit logs are exported."""

    exported_by: UUID
    tenant_id: UUID
    filter_criteria: dict
    record_count: int
    created_at: datetime


__all__ = [
    "AuditLogCreated",
    "AuditLogsExported",
]
