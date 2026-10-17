"""
Tenant module service.

Business logic for tenant context resolution and switching.
"""

from __future__ import annotations

from typing import Optional
from uuid import UUID

from app.core.audit import AuditService
from app.core.exceptions import NotFoundError
from app.core.interfaces import IDatabaseService
from app.modules.tenant.events import TenantContextResolved, TenantSwitched
from app.modules.tenant.repositories import TenantContextRepository
from app.modules.tenant.schemas import (
    TenantContext,
    TenantHealthResponse,
)


class TenantContextService:
    """Service for tenant context resolution and switching."""

    def __init__(
        self,
        repository: TenantContextRepository,
        audit_service: Optional[AuditService] = None,
        db_service: Optional[IDatabaseService] = None,
    ):
        self.repository = repository
        self._audit_service = audit_service
        self._db_service = db_service
        self._events: list = []

    def _publish_event(self, event) -> None:
        self._events.append(event)

    async def resolve_context(self, tenant_id: UUID) -> TenantContext:
        """Resolve full tenant context for a tenant ID."""
        tenant = await self.repository.get_tenant(tenant_id)
        if not tenant:
            raise NotFoundError(f"Tenant with ID {tenant_id} not found")

        total_users = await self.repository.count_users(tenant_id)
        active_users = await self.repository.count_active_users(tenant_id)

        context = TenantContext(
            tenant_id=tenant.id,
            tenant_name=tenant.name,
            tenant_slug=tenant.slug,
            status=tenant.status.value,
            plan=tenant.plan,
            is_platform=tenant.is_platform,
            user_count=total_users,
            active_user_count=active_users,
            created_at=tenant.created_at,
        )

        self._publish_event(
            TenantContextResolved(
                tenant_id=tenant.id,
                resolved_at=tenant.created_at or __import__("datetime").datetime.now(),
            )
        )

        return context

    async def switch_context(
        self,
        tenant_id: UUID,
        actor_user_id: Optional[UUID] = None,
    ) -> TenantContext:
        """Switch to a different tenant context."""
        context = await self.resolve_context(tenant_id)

        self._publish_event(
            TenantSwitched(
                tenant_id=tenant_id,
                switched_by=actor_user_id,
                switched_at=__import__("datetime").datetime.now(),
            )
        )

        return context

    async def get_health(self, tenant_id: UUID) -> TenantHealthResponse:
        """Get tenant health status."""
        tenant = await self.repository.get_tenant(tenant_id)
        if not tenant:
            raise NotFoundError(f"Tenant with ID {tenant_id} not found")

        total_users = await self.repository.count_users(tenant_id)
        active_users = await self.repository.count_active_users(tenant_id)
        mfa_users = await self.repository.count_mfa_enabled(tenant_id)
        locked_users = await self.repository.count_locked_users(tenant_id)

        healthy = tenant.status == "ACTIVE" and locked_users == 0

        return TenantHealthResponse(
            tenant_id=tenant.id,
            status=tenant.status.value,
            healthy=healthy,
            active_users=active_users,
            total_users=total_users,
            mfa_enabled_users=mfa_users,
            locked_users=locked_users,
            message=(
                "Tenant is healthy"
                if healthy
                else (
                    f"Tenant status is {tenant.status.value} "
                    f"with {locked_users} locked users"
                )
            ),
        )


__all__ = ["TenantContextService"]
