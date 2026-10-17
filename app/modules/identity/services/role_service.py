"""
Role service — business logic layer for role and permission management.

Handles role CRUD, permission assignment to roles, and user-role
relationship management within a tenant context.
"""
from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from app.core.audit import AuditService
from app.core.exceptions import ConflictError, NotFoundError
from app.core.security.permissions import Permission
from app.models.user import RoleModel
from app.modules.identity.events import RoleCreated, RoleDeleted, RoleUpdated
from app.modules.identity.repositories.role_repository import RoleRepositoryProtocol
from app.modules.identity.schemas import (
    PermissionOut,
    RoleCreate,
    RolePermissionListResponse,
    RolePermissionOut,
    RoleResponse,
    RoleUpdate,
)


class RoleService:
    """Service for role entities within a tenant."""

    def __init__(
        self,
        role_repository: RoleRepositoryProtocol,
        audit_service: AuditService | None = None,
    ):
        self.role_repository = role_repository
        self._audit_service = audit_service
        self._events: list = []

    def _publish_event(self, event) -> None:
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

    def _to_dict(self, role: RoleModel) -> dict:
        return {
            "id": str(role.id),
            "code": role.code,
            "name": role.name,
            "description": role.description,
            "is_system": role.is_system,
            "is_active": role.is_active,
            "level": role.level,
            "tenant_id": str(role.tenant_id),
            "created_at": role.created_at.isoformat() if role.created_at else None,
            "updated_at": role.updated_at.isoformat() if role.updated_at else None,
        }

    # ---- Role Queries ------------------------------------------------------ #

    async def get(self, id: UUID) -> RoleResponse:
        """Get a role by ID."""
        role = await self.role_repository.get(id)
        if not role:
            raise NotFoundError(f"Role with ID {id} not found")

        await self._record_audit(
            action="role.view",
            resource="role",
            resource_id=str(id),
            description=f"Retrieved role {id}",
            tenant_id=role.tenant_id,
        )
        return RoleResponse.model_validate(role)

    async def get_by_code(self, tenant_id: UUID, code: str) -> RoleModel | None:
        """Get a role by code within a tenant."""
        return await self.role_repository.get_by_code(tenant_id, code)

    async def get_multi_by_tenant(
        self,
        tenant_id: UUID,
        skip: int = 0,
        limit: int = 100,
    ) -> list[RoleResponse]:
        """Get multiple roles for a tenant."""
        roles = await self.role_repository.get_multi_by_tenant(tenant_id, skip=skip, limit=limit)
        return [RoleResponse.model_validate(r) for r in roles]

    async def list_permissions(self, role_id: UUID) -> list[PermissionOut]:
        """List all permissions assigned to a role."""
        role = await self.role_repository.get(role_id)
        if not role:
            raise NotFoundError(f"Role with ID {role_id} not found")

        role_perms = await self.role_repository.get_permissions(role_id)
        return [
            PermissionOut(
                code=rp.permission.code,
                name=rp.permission.name,
            )
            for rp in role_perms
            if rp.permission is not None
        ]

    async def list_users(self, role_id: UUID) -> list[dict]:
        """List users with a given role."""
        role = await self.role_repository.get(role_id)
        if not role:
            raise NotFoundError(f"Role with ID {role_id} not found")

        user_roles = await self.role_repository.get_role_users(role_id)
        results: list[dict] = []
        for user, link in user_roles:
            results.append({
                "id": str(user.id),
                "email": user.email,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "assigned_at": link.created_at,
            })
        return results

    # ---- Role Mutations ---------------------------------------------------- #

    async def create(
        self,
        obj_in: RoleCreate,
        tenant_id: UUID,
        actor_user_id: UUID | None = None,
    ) -> RoleResponse:
        """Create a new role within a tenant."""
        existing = await self.role_repository.get_by_code(tenant_id, obj_in.code)
        if existing:
            raise ConflictError(f"Role with code '{obj_in.code}' already exists in tenant")

        role = await self.role_repository.create(obj_in, tenant_id)

        await self._record_audit(
            action="role.create",
            resource="role",
            resource_id=str(role.id),
            description=f"Created role '{role.code}'",
            after_state=self._to_dict(role),
            tenant_id=tenant_id,
            actor_user_id=actor_user_id,
        )
        self._publish_event(RoleCreated(
            role_id=role.id, role_code=role.code,
            tenant_id=tenant_id, created_at=role.created_at or datetime.now(UTC),
        ))
        return RoleResponse.model_validate(role)

    async def update(
        self,
        id: UUID,
        obj_in: RoleUpdate,
        actor_user_id: UUID | None = None,
    ) -> RoleResponse:
        """Update a role."""
        role = await self.role_repository.get(id)
        if not role:
            raise NotFoundError(f"Role with ID {id} not found")

        before_state = self._to_dict(role)
        updated_role = await self.role_repository.update(role, obj_in)

        await self._record_audit(
            action="role.update",
            resource="role",
            resource_id=str(id),
            description=f"Updated role '{updated_role.code}'",
            before_state=before_state,
            after_state=self._to_dict(updated_role),
            tenant_id=updated_role.tenant_id,
            actor_user_id=actor_user_id,
        )
        self._publish_event(RoleUpdated(
            role_id=updated_role.id, role_code=updated_role.code,
            tenant_id=updated_role.tenant_id, updated_at=updated_role.updated_at or datetime.now(UTC),
        ))
        return RoleResponse.model_validate(updated_role)

    async def delete(
        self,
        id: UUID,
        actor_user_id: UUID | None = None,
    ) -> bool:
        """Delete a role."""
        role = await self.role_repository.get(id)
        if not role:
            raise NotFoundError(f"Role with ID {id} not found")

        if role.is_system:
            raise ConflictError("Cannot delete system roles")

        before_state = self._to_dict(role)
        result = await self.role_repository.delete(role)

        await self._record_audit(
            action="role.delete",
            resource="role",
            resource_id=str(id),
            description=f"Deleted role '{role.code}'",
            before_state=before_state,
            tenant_id=role.tenant_id,
            actor_user_id=actor_user_id,
        )
        self._publish_event(RoleDeleted(
            role_id=role.id, role_code=role.code,
            tenant_id=role.tenant_id, deleted_at=datetime.now(UTC),
        ))
        return result

    # ---- Permission Assignment ------------------------------------------- #

    async def assign_permissions(
        self,
        role_id: UUID,
        permissions: list[str],
        actor_user_id: UUID | None = None,
    ) -> RolePermissionListResponse:
        """Assign permissions to a role."""
        role = await self.role_repository.get(role_id)
        if not role:
            raise NotFoundError(f"Role with ID {role_id} not found")

        # Validate permission codes
        valid_permissions = set(Permission.values()) if hasattr(Permission, 'values') else {p.value for p in Permission}

        for perm in permissions:
            if perm not in valid_permissions:
                raise ConflictError(f"Unknown permission code: '{perm}'")

        await self.role_repository.assign_permissions(role_id, permissions)

        await self._record_audit(
            action="role.permission_assign",
            resource="role",
            resource_id=str(role_id),
            description=f"Assigned permissions {permissions} to role '{role.code}'",
            tenant_id=role.tenant_id,
            actor_user_id=actor_user_id,
        )

        role_perms = await self.role_repository.get_permissions(role_id)
        results = [
            RolePermissionOut(
                id=rp.id,
                role_id=rp.role_id,
                permission=PermissionOut(
                    code=rp.permission.code,
                    name=rp.permission.name,
                ),
            )
            for rp in role_perms
            if rp.permission is not None
        ]
        return RolePermissionListResponse(
            role_id=role_id,
            role_code=role.code,
            permissions=results,
        )

    async def revoke_permissions(
        self,
        role_id: UUID,
        permissions: list[str],
        actor_user_id: UUID | None = None,
    ) -> RolePermissionListResponse:
        """Revoke permissions from a role."""
        role = await self.role_repository.get(role_id)
        if not role:
            raise NotFoundError(f"Role with ID {role_id} not found")

        removed = await self.role_repository.remove_permissions(role_id, permissions)

        await self._record_audit(
            action="role.permission_revoke",
            resource="role",
            resource_id=str(role_id),
            description=f"Removed {removed} permissions from role '{role.code}'",
            tenant_id=role.tenant_id,
            actor_user_id=actor_user_id,
        )

        role_perms = await self.role_repository.get_permissions(role_id)
        results = [
            RolePermissionOut(
                id=rp.id,
                role_id=rp.role_id,
                permission=PermissionOut(
                    code=rp.permission.code,
                    name=rp.permission.name,
                ),
            )
            for rp in role_perms
            if rp.permission is not None
        ]
        return RolePermissionListResponse(
            role_id=role_id,
            role_code=role.code,
            permissions=results,
        )

    async def set_active(
        self,
        id: UUID,
        is_active: bool,
        actor_user_id: UUID | None = None,
    ) -> RoleResponse:
        """Activate or deactivate a role."""
        role = await self.role_repository.get(id)
        if not role:
            raise NotFoundError(f"Role with ID {id} not found")

        if role.is_system:
            raise ConflictError("Cannot modify system roles")

        before_state = self._to_dict(role)
        updated_role = await self.role_repository.set_active(role, is_active)

        await self._record_audit(
            action="role.status_change",
            resource="role",
            resource_id=str(id),
            description=f"Role {'activated' if is_active else 'deactivated'}",
            before_state=before_state,
            after_state=self._to_dict(updated_role),
            tenant_id=updated_role.tenant_id,
            actor_user_id=actor_user_id,
        )
        return RoleResponse.model_validate(updated_role)


__all__ = ["RoleService"]
