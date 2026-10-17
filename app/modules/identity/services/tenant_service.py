"""
Tenant service — business logic layer for tenant management.

Follows SOLID principles:
- SRP: Only handles tenant domain logic
- OCP: Extensible via repository interface implementation
- LSP: Repository interfaces can be swapped
- ISP: Depends on abstract repository interface
- DIP: Depends on abstractions (repository, audit), not concretions
"""
from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from uuid import UUID

from app.core.audit import AuditService
from app.core.exceptions import BadRequestError, ConflictError, NotFoundError
from app.core.interfaces import IDatabaseService
from app.models.enums import TenantStatus
from app.models.tenant import Tenant
from app.modules.identity.events import (
    TenantCreated,
    TenantDeleted,
    TenantStatusChanged,
    TenantUpdated,
)
from app.modules.identity.repositories.tenant_repository import TenantRepositoryProtocol
from app.modules.identity.schemas import (
    TenantCreate,
    TenantResponse,
    TenantSettings,
    TenantStatsResponse,
    TenantStatusUpdate,
    TenantUpdate,
)


class TenantService:
    """Service for tenant entities.

    Orchestrates business logic, validation, and audit logging for tenants.
    """

    def __init__(
        self,
        repository: TenantRepositoryProtocol,
        audit_service: AuditService | None = None,
        db_service: IDatabaseService | None = None,
    ):
        self.repository = repository
        self._audit_service = audit_service
        self._db_service = db_service
        self._events: list = []

    def _publish_event(self, event) -> None:
        """Queue a domain event (in-process event bus placeholder)."""
        self._events.append(event)

    async def _record_audit(
        self,
        action: str,
        resource: str,
        resource_id: str | None = None,
        description: str | None = None,
        before_state: dict | None = None,
        after_state: dict | None = None,
        tenant_id: UUID | None = None,
        actor_user_id: UUID | None = None,
    ) -> None:
        """Record an audit event if audit service is available."""
        if self._audit_service and tenant_id:
            try:
                await self._audit_service.record_audit(
                    tenant_id=tenant_id,
                    action=action,
                    resource=resource,
                    resource_id=resource_id,
                    description=description,
                    before_state=before_state,
                    after_state=after_state,
                    actor_user_id=actor_user_id,
                )
            except Exception as exc:  # noqa: BLE001
                from app.core.logging import get_logger
                logger = get_logger(__name__)
                logger.error("Failed to record audit event: %s", exc)

    def _to_dict(self, tenant: Tenant) -> dict:
        """Convert tenant to dictionary for audit logging."""
        return {
            "id": str(tenant.id),
            "name": tenant.name,
            "slug": tenant.slug,
            "status": tenant.status.value if tenant.status else None,
            "plan": tenant.plan,
            "is_platform": tenant.is_platform,
            "timezone": tenant.timezone,
            "locale": tenant.locale,
            "created_at": tenant.created_at.isoformat() if tenant.created_at else None,
            "updated_at": tenant.updated_at.isoformat() if tenant.updated_at else None,
        }

    # ---- Queries ----------------------------------------------------------- #

    async def get(self, id: UUID) -> TenantResponse:
        """Get a tenant by ID."""
        tenant = await self.repository.get(id)
        if not tenant:
            raise NotFoundError(f"Tenant with ID {id} not found")

        await self._record_audit(
            action="tenant.view",
            resource="tenant",
            resource_id=str(id),
            description=f"Retrieved tenant {id}",
            tenant_id=tenant.id,
        )
        return TenantResponse.model_validate(tenant)

    async def get_by_slug(self, slug: str) -> TenantResponse:
        """Get a tenant by slug."""
        tenant = await self.repository.get_by_slug(slug)
        if not tenant:
            raise NotFoundError(f"Tenant with slug '{slug}' not found")

        await self._record_audit(
            action="tenant.view_by_slug",
            resource="tenant",
            resource_id=str(tenant.id),
            description=f"Retrieved tenant by slug '{slug}'",
            tenant_id=tenant.id,
        )
        return TenantResponse.model_validate(tenant)

    async def get_by_name(self, name: str) -> TenantResponse:
        """Get a tenant by name (case-insensitive)."""
        tenant = await self.repository.get_by_name(name)
        if not tenant:
            raise NotFoundError(f"Tenant with name '{name}' not found")
        return TenantResponse.model_validate(tenant)

    async def get_multi(
        self,
        skip: int = 0,
        limit: int = 100,
        status: TenantStatus | None = None,
    ) -> list[TenantResponse]:
        """Get multiple tenants, optionally filtered by status."""
        tenants = await self.repository.get_multi(skip=skip, limit=limit, status=status)
        return [TenantResponse.model_validate(t) for t in tenants]

    async def search(
        self,
        query: str,
        skip: int = 0,
        limit: int = 100,
    ) -> list[TenantResponse]:
        """Search tenants by name, slug, or plan."""
        if not query or len(query.strip()) < 2:
            raise BadRequestError("Search query must be at least 2 characters")
        tenants = await self.repository.search(query.strip(), skip=skip, limit=limit)
        return [TenantResponse.model_validate(t) for t in tenants]

    async def get_stats(self, id: UUID) -> TenantStatsResponse:
        """Get aggregate statistics for a tenant."""
        tenant = await self.repository.get(id)
        if not tenant:
            raise NotFoundError(f"Tenant with ID {id} not found")

        total_users, active_users, locked_users, mfa_users, admin_users, must_change, mfa_req = (
            await asyncio.gather(
                self.repository.count_users_all(tenant_id=id),
                self.repository.count_users(tenant_id=id),
                self.repository.count_locked_users(tenant_id=id),
                self.repository.count_mfa_enabled(tenant_id=id),
                self.repository.count_admin_users(tenant_id=id),
                self.repository.count_must_change(tenant_id=id),
                self.repository.count_mfa_required(tenant_id=id),
            )
        )

        return TenantStatsResponse(
            tenant_id=tenant.id,
            total_users=total_users,
            active_users=active_users,
            inactive_users=total_users - active_users,
            locked_users=locked_users,
            mfa_enabled_users=mfa_users,
            admin_users=admin_users,
            must_change_password=must_change,
            mfa_enrollment_required=mfa_req,
            created_at=tenant.created_at,
            updated_at=tenant.updated_at,
        )

    # ---- Mutations --------------------------------------------------------- #

    async def create(
        self,
        obj_in: TenantCreate,
        actor_user_id: UUID | None = None,
    ) -> TenantResponse:
        """Create a new tenant."""
        existing = await self.repository.get_by_slug(obj_in.slug)
        if existing:
            raise ConflictError(f"Tenant with slug '{obj_in.slug}' already exists")

        existing_name = await self.repository.get_by_name(obj_in.name)
        if existing_name:
            raise ConflictError(f"Tenant with name '{obj_in.name}' already exists")

        tenant = await self.repository.create(obj_in)

        await self._record_audit(
            action="tenant.create",
            resource="tenant",
            resource_id=str(tenant.id),
            description=f"Created tenant '{tenant.name}' (slug={tenant.slug})",
            before_state=None,
            after_state=self._to_dict(tenant),
            tenant_id=tenant.id,
            actor_user_id=actor_user_id,
        )
        self._publish_event(TenantCreated(
            tenant_id=tenant.id, name=tenant.name, created_at=tenant.created_at or datetime.now(UTC)
        ))
        return TenantResponse.model_validate(tenant)

    async def update(
        self,
        id: UUID,
        obj_in: TenantUpdate,
        actor_user_id: UUID | None = None,
    ) -> TenantResponse:
        """Update a tenant."""
        tenant = await self.repository.get(id)
        if not tenant:
            raise NotFoundError(f"Tenant with ID {id} not found")

        if obj_in.slug and obj_in.slug != tenant.slug:
            existing = await self.repository.get_by_slug(obj_in.slug)
            if existing:
                raise ConflictError(f"Tenant with slug '{obj_in.slug}' already exists")

        before_state = self._to_dict(tenant)
        updated_tenant = await self.repository.update(tenant, obj_in)

        await self._record_audit(
            action="tenant.update",
            resource="tenant",
            resource_id=str(id),
            description=f"Updated tenant {id}",
            before_state=before_state,
            after_state=self._to_dict(updated_tenant),
            tenant_id=updated_tenant.id,
            actor_user_id=actor_user_id,
        )
        self._publish_event(TenantUpdated(
            tenant_id=updated_tenant.id,
            name=updated_tenant.name,
            updated_at=updated_tenant.updated_at or datetime.now(UTC),
        ))
        return TenantResponse.model_validate(updated_tenant)

    async def update_status(
        self,
        id: UUID,
        obj_in: TenantStatusUpdate,
        actor_user_id: UUID | None = None,
    ) -> TenantResponse:
        """Update a tenant's lifecycle status."""
        tenant = await self.repository.get(id)
        if not tenant:
            raise NotFoundError(f"Tenant with ID {id} not found")

        if tenant.status == obj_in.status:
            return TenantResponse.model_validate(tenant)

        before_state = self._to_dict(tenant)
        updated_tenant = await self.repository.update_status(tenant, obj_in.status, obj_in.reason)

        await self._record_audit(
            action="tenant.status_change",
            resource="tenant",
            resource_id=str(id),
            description=f"Status changed from {tenant.status} to {obj_in.status}"
            + (f": {obj_in.reason}" if obj_in.reason else ""),
            before_state=before_state,
            after_state=self._to_dict(updated_tenant),
            tenant_id=id,
            actor_user_id=actor_user_id,
        )
        self._publish_event(TenantStatusChanged(
            tenant_id=id,
            status=obj_in.status.value,
            changed_at=datetime.now(UTC),
        ))
        return TenantResponse.model_validate(updated_tenant)

    async def update_settings(
        self,
        id: UUID,
        obj_in: TenantSettings,
        actor_user_id: UUID | None = None,
    ) -> TenantResponse:
        """Update tenant settings (timezone, locale, plan, password policy)."""
        tenant = await self.repository.get(id)
        if not tenant:
            raise NotFoundError(f"Tenant with ID {id} not found")

        before_state = self._to_dict(tenant)
        updated_tenant = await self.repository.update_settings(tenant, obj_in)

        await self._record_audit(
            action="tenant.settings_update",
            resource="tenant",
            resource_id=str(id),
            description="Updated tenant settings",
            before_state=before_state,
            after_state=self._to_dict(updated_tenant),
            tenant_id=id,
            actor_user_id=actor_user_id,
        )
        return TenantResponse.model_validate(updated_tenant)

    async def delete(
        self,
        id: UUID,
        actor_user_id: UUID | None = None,
    ) -> bool:
        """Delete a tenant."""
        tenant = await self.repository.get(id)
        if not tenant:
            raise NotFoundError(f"Tenant with ID {id} not found")

        before_state = self._to_dict(tenant)
        result = await self.repository.delete(tenant)

        await self._record_audit(
            action="tenant.delete",
            resource="tenant",
            resource_id=str(id),
            description=f"Deleted tenant '{tenant.name}' (id={id})",
            before_state=before_state,
            after_state=None,
            tenant_id=id,
            actor_user_id=actor_user_id,
        )
        self._publish_event(TenantDeleted(
            tenant_id=id, deleted_at=datetime.now(UTC)
        ))
        return result


__all__ = ["TenantService"]
