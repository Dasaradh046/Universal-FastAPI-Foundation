"""
Repository for the audit module.

Data-access layer following the Repository pattern with dependency inversion.
"""

from __future__ import annotations

from typing import List, Optional, Protocol
from uuid import UUID
from datetime import datetime

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit import AuditLog
from app.modules.audit.schemas import AuditLogCreate, AuditLogFilter


class AuditRepository:
    """Repository for audit log entities.

    Implements the data-access layer for the AuditLog entity.
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get(self, id: UUID) -> Optional[AuditLog]:
        """Get an audit log by ID."""
        stmt = select(AuditLog).where(AuditLog.id == id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def create(self, obj_in: AuditLogCreate) -> AuditLog:
        """Create a new audit log entry."""
        import json

        before_json = json.dumps(obj_in.before_state, default=str) if obj_in.before_state else None
        after_json = json.dumps(obj_in.after_state, default=str) if obj_in.after_state else None

        db_obj = AuditLog(
            tenant_id=obj_in.tenant_id,
            action=obj_in.action,
            resource=obj_in.resource,
            resource_id=obj_in.resource_id,
            description=obj_in.description,
            before_state=before_json,
            after_state=after_json,
            ip_address=obj_in.ip_address,
            user_agent=obj_in.user_agent,
            actor_user_id=obj_in.actor_user_id,
        )
        self.db.add(db_obj)
        await self.db.flush()
        await self.db.refresh(db_obj)
        return db_obj

    async def get_multi(
        self,
        tenant_id: UUID,
        filters: AuditLogFilter | None = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[AuditLog]:
        """Get multiple audit logs for a tenant with optional filters."""
        stmt = select(AuditLog).where(AuditLog.tenant_id == tenant_id)

        if filters:
            if filters.action:
                stmt = stmt.where(AuditLog.action == filters.action)
            if filters.resource:
                stmt = stmt.where(AuditLog.resource == filters.resource)
            if filters.resource_id:
                stmt = stmt.where(AuditLog.resource_id == filters.resource_id)
            if filters.actor_user_id:
                stmt = stmt.where(AuditLog.actor_user_id == filters.actor_user_id)
            if filters.start_date:
                stmt = stmt.where(AuditLog.created_at >= filters.start_date)
            if filters.end_date:
                stmt = stmt.where(AuditLog.created_at <= filters.end_date)
            if filters.ip_address:
                stmt = stmt.where(AuditLog.ip_address == filters.ip_address)

        stmt = stmt.order_by(AuditLog.created_at.desc()).offset(skip).limit(limit)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def count(
        self,
        tenant_id: UUID,
        filters: AuditLogFilter | None = None
    ) -> int:
        """Count audit logs for a tenant with optional filters."""
        stmt = select(func.count()).select_from(AuditLog).where(AuditLog.tenant_id == tenant_id)

        if filters:
            if filters.action:
                stmt = stmt.where(AuditLog.action == filters.action)
            if filters.resource:
                stmt = stmt.where(AuditLog.resource == filters.resource)
            if filters.resource_id:
                stmt = stmt.where(AuditLog.resource_id == filters.resource_id)
            if filters.actor_user_id:
                stmt = stmt.where(AuditLog.actor_user_id == filters.actor_user_id)
            if filters.start_date:
                stmt = stmt.where(AuditLog.created_at >= filters.start_date)
            if filters.end_date:
                stmt = stmt.where(AuditLog.created_at <= filters.end_date)
            if filters.ip_address:
                stmt = stmt.where(AuditLog.ip_address == filters.ip_address)

        result = await self.db.execute(stmt)
        return int(result.scalar_one())


class AuditRepositoryProtocol(Protocol):
    """Protocol for audit repository - enables dependency inversion."""

    async def get(self, id: UUID) -> Optional[AuditLog]: ...
    async def create(self, obj_in: AuditLogCreate) -> AuditLog: ...
    async def get_multi(self, tenant_id: UUID, filters: AuditLogFilter | None, skip: int, limit: int) -> List[AuditLog]: ...
    async def count(self, tenant_id: UUID, filters: AuditLogFilter | None) -> int: ...


__all__ = ["AuditRepository", "AuditRepositoryProtocol"]