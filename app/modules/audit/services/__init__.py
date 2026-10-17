"""
Service layer for the audit module.

Follows SOLID principles:
- SRP: Only handles audit domain logic
- OCP: Extensible via interface implementation
- LSP: Repository interface can be swapped
- ISP: Depends on abstract repository interface
- DIP: Depends on abstractions (repository), not concretions
"""

from __future__ import annotations

from typing import List, Optional
from uuid import UUID

from app.core.audit import AuditService
from app.core.exceptions import NotFoundError
from app.core.interfaces import IDatabaseService
from app.modules.audit.repositories import AuditRepository, AuditRepositoryProtocol
from app.modules.audit.schemas import (
    AuditLogCreate,
    AuditLogFilter,
    AuditLogResponse,
    AuditLogResponseEnvelope,
    AuditLogListResponseEnvelope,
)
from app.models.audit import AuditLog


class AuditServiceModule:
    """Service for audit log entities.

    Orchestrates business logic for audit log querying and management.
    """

    def __init__(
        self,
        repository: AuditRepositoryProtocol,
        audit_service: Optional[AuditService] = None,
        db_service: Optional[IDatabaseService] = None,
    ):
        self.repository = repository
        self._audit_service = audit_service
        self._db_service = db_service

    async def create_log(
        self,
        obj_in: AuditLogCreate,
    ) -> AuditLogResponse:
        """Create a new audit log entry."""
        audit_log = await self.repository.create(obj_in)
        return AuditLogResponse.model_validate(audit_log)

    async def get_log(
        self,
        id: UUID,
        tenant_id: UUID,
    ) -> AuditLogResponse:
        """Get an audit log by ID within a tenant."""
        audit_log = await self.repository.get(id)
        if not audit_log or audit_log.tenant_id != tenant_id:
            raise NotFoundError(f"Audit log with ID {id} not found in tenant {tenant_id}")

        return AuditLogResponse.model_validate(audit_log)

    async def get_logs(
        self,
        tenant_id: UUID,
        filters: AuditLogFilter | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> List[AuditLogResponse]:
        """Get multiple audit logs for a tenant with optional filters."""
        logs = await self.repository.get_multi(tenant_id, filters, skip=skip, limit=limit)
        return [AuditLogResponse.model_validate(log) for log in logs]

    async def count_logs(
        self,
        tenant_id: UUID,
        filters: AuditLogFilter | None = None,
    ) -> int:
        """Count audit logs for a tenant with optional filters."""
        return await self.repository.count(tenant_id, filters)


__all__ = ["AuditServiceModule"]
