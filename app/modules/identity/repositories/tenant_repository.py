"""
Tenant repository — data-access layer for tenant entities.

Uses centralized models from ``app.models``. All queries are scoped
appropriately for the platform-wide (non-tenant-scored) tenant table.
"""
from __future__ import annotations

from typing import Protocol
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security.encryption import encrypt_field
from app.models.enums import TenantStatus
from app.models.tenant import Tenant
from app.models.user import User
from app.modules.identity.schemas import (
    TenantCreate,
    TenantSettings,
    TenantUpdate,
)

_ENCRYPTED_FIELDS: dict[str, str] = {
    "billing_email": "billing_email_encrypted",
    "billing_address": "billing_address_encrypted",
    "tax_id": "tax_id_encrypted",
    "primary_contact_phone": "primary_contact_phone_encrypted",
}


class TenantRepository:
    """Repository for tenant entities."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get(self, id: UUID) -> Tenant | None:
        """Get a tenant by ID."""
        stmt = select(Tenant).where(Tenant.id == id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_slug(self, slug: str) -> Tenant | None:
        """Get a tenant by slug."""
        stmt = select(Tenant).where(Tenant.slug == slug)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_name(self, name: str) -> Tenant | None:
        """Get a tenant by name (case-insensitive)."""
        stmt = select(Tenant).where(func.lower(Tenant.name) == func.lower(name))
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_multi(
        self,
        skip: int = 0,
        limit: int = 100,
        status: TenantStatus | None = None,
    ) -> list[Tenant]:
        """Get multiple tenants, optionally filtered by status."""
        stmt = select(Tenant)
        if status:
            stmt = stmt.where(Tenant.status == status)
        stmt = stmt.order_by(Tenant.created_at.desc()).offset(skip).limit(limit)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def search(self, query: str, skip: int = 0, limit: int = 100) -> list[Tenant]:
        """Search tenants by name, slug, or plan."""
        pattern = f"%{query}%"
        stmt = (
            select(Tenant)
            .where(
                func.lower(Tenant.name).like(func.lower(pattern))
                | func.lower(Tenant.slug).like(func.lower(pattern))
                | func.lower(func.coalesce(Tenant.plan, "")).like(func.lower(pattern))
            )
            .order_by(Tenant.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def create(self, obj_in: TenantCreate) -> Tenant:
        """Create a new tenant."""
        data = obj_in.model_dump(exclude_unset=True)

        # Ensure defaults
        data.setdefault("timezone", "UTC")
        data.setdefault("locale", "en-US")
        data.setdefault("status", TenantStatus.ACTIVE)

        # Move plaintext encrypted fields to their *_encrypted columns
        encrypted: dict[str, str] = {}
        for plain_field, enc_field in _ENCRYPTED_FIELDS.items():
            if plain_field in data and data[plain_field] is not None:
                encrypted[enc_field] = encrypt_field(data.pop(plain_field))
        data.update(encrypted)

        db_obj = Tenant(**data)
        self.db.add(db_obj)
        await self.db.flush()
        await self.db.refresh(db_obj)
        return db_obj

    async def update(
        self,
        db_obj: Tenant,
        obj_in: TenantUpdate,
    ) -> Tenant:
        """Update a tenant."""
        data = obj_in.model_dump(exclude_unset=True)

        encrypted: dict[str, str] = {}
        for plain_field, enc_field in _ENCRYPTED_FIELDS.items():
            if plain_field in data and data[plain_field] is not None:
                encrypted[enc_field] = encrypt_field(data.pop(plain_field))
        data.update(encrypted)

        for field, value in data.items():
            setattr(db_obj, field, value)
        self.db.add(db_obj)
        await self.db.flush()
        await self.db.refresh(db_obj)
        return db_obj

    async def update_status(
        self,
        db_obj: Tenant,
        status: TenantStatus,
        reason: str | None = None,
    ) -> Tenant:
        """Update a tenant's lifecycle status."""
        db_obj.status = status
        self.db.add(db_obj)
        await self.db.flush()
        await self.db.refresh(db_obj)
        return db_obj

    async def update_settings(
        self,
        db_obj: Tenant,
        obj_in: TenantSettings,
    ) -> Tenant:
        """Update tenant settings (timezone, locale, plan, password_policy_id)."""
        data = obj_in.model_dump(exclude_unset=True)
        for field, value in data.items():
            setattr(db_obj, field, value)
        self.db.add(db_obj)
        await self.db.flush()
        await self.db.refresh(db_obj)
        return db_obj

    async def set_platform_flag(self, db_obj: Tenant, is_platform: bool) -> Tenant:
        """Set the platform flag on a tenant."""
        db_obj.is_platform = is_platform
        self.db.add(db_obj)
        await self.db.flush()
        await self.db.refresh(db_obj)
        return db_obj

    async def delete(self, db_obj: Tenant) -> bool:
        """Delete a tenant."""
        await self.db.delete(db_obj)
        await self.db.flush()
        return True

    async def count(self, status: TenantStatus | None = None) -> int:
        """Count total tenants."""
        stmt = select(func.count()).select_from(Tenant)
        if status:
            stmt = stmt.where(Tenant.status == status)
        result = await self.db.execute(stmt)
        return int(result.scalar_one())

    async def count_users(self, tenant_id: UUID) -> int:
        """Count active users in a tenant."""
        stmt = (
            select(func.count())
            .select_from(User)
            .where(User.tenant_id == tenant_id, User.is_active == True)
        )
        result = await self.db.execute(stmt)
        return int(result.scalar_one())

    async def count_users_all(self, tenant_id: UUID) -> int:
        """Count ALL users (active + inactive) in a tenant."""
        stmt = select(func.count()).select_from(User).where(User.tenant_id == tenant_id)
        result = await self.db.execute(stmt)
        return int(result.scalar_one())

    async def count_locked_users(self, tenant_id: UUID) -> int:
        """Count locked-out users in a tenant."""
        stmt = (
            select(func.count())
            .select_from(User)
            .where(User.tenant_id == tenant_id, User.locked_out_at.is_not(None))
        )
        result = await self.db.execute(stmt)
        return int(result.scalar_one())

    async def count_mfa_enabled(self, tenant_id: UUID) -> int:
        """Count MFA-enabled users in a tenant."""
        stmt = (
            select(func.count())
            .select_from(User)
            .where(User.tenant_id == tenant_id, User.two_factor_enabled == True)
        )
        result = await self.db.execute(stmt)
        return int(result.scalar_one())

    async def count_admin_users(self, tenant_id: UUID) -> int:
        """Count super-admin users in a tenant."""
        stmt = (
            select(func.count())
            .select_from(User)
            .where(User.tenant_id == tenant_id, User.is_super_admin == True)
        )
        result = await self.db.execute(stmt)
        return int(result.scalar_one())

    async def count_must_change(self, tenant_id: UUID) -> int:
        """Count users requiring password change in a tenant."""
        stmt = (
            select(func.count())
            .select_from(User)
            .where(
                User.tenant_id == tenant_id,
                User.must_change_password == True,
            )
        )
        result = await self.db.execute(stmt)
        return int(result.scalar_one())

    async def count_mfa_required(self, tenant_id: UUID) -> int:
        """Count users with mfa_enrollment_required flag in a tenant."""
        stmt = (
            select(func.count())
            .select_from(User)
            .where(
                User.tenant_id == tenant_id,
                User.mfa_enrollment_required == True,
            )
        )
        result = await self.db.execute(stmt)
        return int(result.scalar_one())


class TenantRepositoryProtocol(Protocol):
    """Protocol for tenant repository — enables dependency inversion."""

    async def get(self, id: UUID) -> Tenant | None: ...
    async def get_by_slug(self, slug: str) -> Tenant | None: ...
    async def get_by_name(self, name: str) -> Tenant | None: ...
    async def get_multi(self, skip: int, limit: int, status: TenantStatus | None) -> list[Tenant]: ...
    async def search(self, query: str, skip: int, limit: int) -> list[Tenant]: ...
    async def create(self, obj_in: TenantCreate) -> Tenant: ...
    async def update(self, db_obj: Tenant, obj_in: TenantUpdate) -> Tenant: ...
    async def update_status(self, db_obj: Tenant, status: TenantStatus, reason: str | None) -> Tenant: ...
    async def update_settings(self, db_obj: Tenant, obj_in: TenantSettings) -> Tenant: ...
    async def set_platform_flag(self, db_obj: Tenant, is_platform: bool) -> Tenant: ...
    async def delete(self, db_obj: Tenant) -> bool: ...
    async def count(self, status: TenantStatus | None) -> int: ...
    async def count_users(self, tenant_id: UUID) -> int: ...
    async def count_users_all(self, tenant_id: UUID) -> int: ...
    async def count_locked_users(self, tenant_id: UUID) -> int: ...
    async def count_mfa_enabled(self, tenant_id: UUID) -> int: ...
    async def count_admin_users(self, tenant_id: UUID) -> int: ...
    async def count_must_change(self, tenant_id: UUID) -> int: ...
    async def count_mfa_required(self, tenant_id: UUID) -> int: ...


__all__ = ["TenantRepository", "TenantRepositoryProtocol"]
