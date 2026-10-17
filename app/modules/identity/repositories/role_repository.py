"""
Role repository — data-access layer for role and permission entities.

Handles tenant-scoped role definitions, role-permission assignments,
and user-role (additional roles) links.
"""
from __future__ import annotations

from typing import Protocol
from uuid import UUID

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import Permission, RoleModel, RolePermission, UserRole
from app.modules.identity.schemas import RoleCreate, RoleUpdate


class RoleRepository:
    """Repository for role and permission entities."""

    def __init__(self, db: AsyncSession):
        self.db = db

    # ---- Role lookups ------------------------------------------------------ #

    async def get(self, id: UUID) -> RoleModel | None:
        """Get a role by ID."""
        stmt = select(RoleModel).where(RoleModel.id == id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_in_tenant(self, tenant_id: UUID, id: UUID) -> RoleModel | None:
        """Get a role by ID within a tenant."""
        stmt = select(RoleModel).where(
            RoleModel.id == id, RoleModel.tenant_id == tenant_id
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_code(self, tenant_id: UUID, code: str) -> RoleModel | None:
        """Get a role by code within a tenant (case-insensitive)."""
        stmt = select(RoleModel).where(
            RoleModel.tenant_id == tenant_id,
            func.lower(RoleModel.code) == func.lower(code),
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_multi(
        self,
        tenant_id: UUID,
        skip: int = 0,
        limit: int = 100,
    ) -> list[RoleModel]:
        """Get all roles for a tenant."""
        stmt = (
            select(RoleModel)
            .where(RoleModel.tenant_id == tenant_id)
            .order_by(RoleModel.code)
            .offset(skip)
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_system_roles(self) -> list[RoleModel]:
        """Get all system-defined roles (no tenant_id required — they are global seed data)."""
        stmt = (
            select(RoleModel)
            .where(RoleModel.is_system == True)
            .order_by(RoleModel.code)
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    # ---- Role mutations ---------------------------------------------------- #

    async def create(self, obj_in: RoleCreate, tenant_id: UUID, is_system: bool = False) -> RoleModel:
        """Create a new tenant-scoped role."""
        db_obj = RoleModel(
            tenant_id=tenant_id,
            code=obj_in.code,
            name=obj_in.name,
            description=obj_in.description,
            is_system=is_system,
        )
        self.db.add(db_obj)
        await self.db.flush()
        await self.db.refresh(db_obj)
        return db_obj

    async def update(
        self,
        db_obj: RoleModel,
        obj_in: RoleUpdate,
    ) -> RoleModel:
        """Update a role."""
        data = obj_in.model_dump(exclude_unset=True)
        for field, value in data.items():
            setattr(db_obj, field, value)
        self.db.add(db_obj)
        await self.db.flush()
        await self.db.refresh(db_obj)
        return db_obj

    async def delete(self, db_obj: RoleModel) -> bool:
        """Delete a role (cascades to role_permissions and user_roles via FK ondelete)."""
        await self.db.delete(db_obj)
        await self.db.flush()
        return True

    async def count_by_tenant(self, tenant_id: UUID) -> int:
        """Count roles in a tenant."""
        stmt = (
            select(func.count())
            .select_from(RoleModel)
            .where(RoleModel.tenant_id == tenant_id)
        )
        result = await self.db.execute(stmt)
        return int(result.scalar_one())

    # ---- Permission lookups ------------------------------------------------ #

    async def get_permission(self, id: UUID) -> Permission | None:
        """Get a permission by ID."""
        stmt = select(Permission).where(Permission.id == id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_permission_by_code(self, tenant_id: UUID, code: str) -> Permission | None:
        """Get a permission by code within a tenant."""
        stmt = select(Permission).where(
            Permission.tenant_id == tenant_id,
            func.lower(Permission.code) == func.lower(code),
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_permissions(self, tenant_id: UUID) -> list[Permission]:
        """Get all permissions for a tenant."""
        stmt = (
            select(Permission)
            .where(Permission.tenant_id == tenant_id)
            .order_by(Permission.module, Permission.code)
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    # ---- Role-permission associations -------------------------------------- #

    async def assign_permission(
        self,
        role_id: UUID,
        permission: Permission,
    ) -> RolePermission:
        """Link a permission to a role (idempotent)."""

        # Use the tenant_id from the permission row (permissions are tenant-scoped)
        stmt = select(RolePermission).where(
            RolePermission.role_id == role_id,
            RolePermission.permission_id == permission.id,
        )
        result = await self.db.execute(stmt)
        existing = result.scalar_one_or_none()
        if existing:
            return existing

        link = RolePermission(
            tenant_id=permission.tenant_id,
            role_id=role_id,
            permission_id=permission.id,
        )
        self.db.add(link)
        await self.db.flush()
        await self.db.refresh(link)
        return link

    async def remove_permission(
        self,
        role_id: UUID,
        permission_id: UUID,
    ) -> int:
        """Remove a permission from a role. Returns rows affected."""
        stmt = (
            delete(RolePermission)
            .where(
                RolePermission.role_id == role_id,
                RolePermission.permission_id == permission_id,
            )
        )
        result = await self.db.execute(stmt)
        return int(result.rowcount)

    async def get_role_permissions(self, role_id: UUID) -> list[Permission]:
        """Get all permissions assigned to a role."""
        stmt = (
            select(Permission)
            .join(RolePermission, RolePermission.permission_id == Permission.id)
            .where(RolePermission.role_id == role_id)
            .order_by(Permission.module, Permission.code)
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    # ---- User-role links (additional roles) -------------------------------- #

    async def assign_user_role(
        self,
        user_id: UUID,
        role_id: UUID,
        tenant_id: UUID,
    ) -> UserRole:
        """Link an additional role to a user (idempotent)."""
        stmt = select(UserRole).where(
            UserRole.user_id == user_id,
            UserRole.role_id == role_id,
        )
        result = await self.db.execute(stmt)
        existing = result.scalar_one_or_none()
        if existing:
            return existing

        link = UserRole(
            tenant_id=tenant_id,
            user_id=user_id,
            role_id=role_id,
        )
        self.db.add(link)
        await self.db.flush()
        await self.db.refresh(link)
        return link

    async def remove_user_role(
        self,
        user_id: UUID,
        role_id: UUID,
    ) -> int:
        """Remove an additional role from a user. Returns rows affected."""
        stmt = (
            delete(UserRole)
            .where(
                UserRole.user_id == user_id,
                UserRole.role_id == role_id,
            )
        )
        result = await self.db.execute(stmt)
        return int(result.rowcount)

    async def get_user_roles(
        self,
        user_id: UUID,
    ) -> list[tuple[RoleModel, UserRole]]:
        """Get all additional roles (with link rows) for a user."""
        stmt = (
            select(RoleModel, UserRole)
            .join(UserRole, UserRole.role_id == RoleModel.id)
            .where(UserRole.user_id == user_id)
            .order_by(RoleModel.code)
        )
        result = await self.db.execute(stmt)
        return list(result.all())


class RoleRepositoryProtocol(Protocol):
    """Protocol for role repository — enables dependency inversion."""

    async def get(self, id: UUID) -> RoleModel | None: ...
    async def get_in_tenant(self, tenant_id: UUID, id: UUID) -> RoleModel | None: ...
    async def get_by_code(self, tenant_id: UUID, code: str) -> RoleModel | None: ...
    async def get_multi(self, tenant_id: UUID, skip: int, limit: int) -> list[RoleModel]: ...
    async def create(self, obj_in: RoleCreate, tenant_id: UUID, is_system: bool) -> RoleModel: ...
    async def update(self, db_obj: RoleModel, obj_in: RoleUpdate) -> RoleModel: ...
    async def delete(self, db_obj: RoleModel) -> bool: ...
    async def count_by_tenant(self, tenant_id: UUID) -> int: ...
    async def get_permission(self, id: UUID) -> Permission | None: ...
    async def get_permission_by_code(self, tenant_id: UUID, code: str) -> Permission | None: ...
    async def get_permissions(self, tenant_id: UUID) -> list[Permission]: ...
    async def assign_permission(self, role_id: UUID, permission: Permission) -> RolePermission: ...
    async def remove_permission(self, role_id: UUID, permission_id: UUID) -> int: ...
    async def get_role_permissions(self, role_id: UUID) -> list[Permission]: ...
    async def assign_user_role(self, user_id: UUID, role_id: UUID, tenant_id: UUID) -> UserRole: ...
    async def remove_user_role(self, user_id: UUID, role_id: UUID) -> int: ...
    async def get_user_roles(self, user_id: UUID) -> list[tuple[RoleModel, UserRole]]: ...


__all__ = ["RoleRepository", "RoleRepositoryProtocol"]
