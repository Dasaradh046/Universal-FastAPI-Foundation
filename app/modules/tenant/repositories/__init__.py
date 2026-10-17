"""
Tenant module repository.

Data-access layer for tenant context resolution.
"""

from __future__ import annotations

from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.tenant import Tenant
from app.models.user import User


class TenantContextRepository:
    """Repository for tenant context data access."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_tenant(self, tenant_id: UUID) -> Optional[Tenant]:
        """Get a tenant by ID."""
        stmt = select(Tenant).where(Tenant.id == tenant_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_tenant_by_slug(self, slug: str) -> Optional[Tenant]:
        """Get a tenant by slug."""
        stmt = select(Tenant).where(Tenant.slug == slug)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def count_users(self, tenant_id: UUID) -> int:
        """Count total users in a tenant."""
        stmt = select(User).where(User.tenant_id == tenant_id)
        result = await self.db.execute(stmt)
        return len(result.scalars().all())

    async def count_active_users(self, tenant_id: UUID) -> int:
        """Count active users in a tenant."""
        stmt = select(User).where(
            User.tenant_id == tenant_id, User.is_active == True  # noqa: E712
        )
        result = await self.db.execute(stmt)
        return len(result.scalars().all())

    async def count_mfa_enabled(self, tenant_id: UUID) -> int:
        """Count MFA-enabled users in a tenant."""
        stmt = select(User).where(
            User.tenant_id == tenant_id, User.two_factor_enabled == True  # noqa: E712
        )
        result = await self.db.execute(stmt)
        return len(result.scalars().all())

    async def count_locked_users(self, tenant_id: UUID) -> int:
        """Count locked-out users in a tenant."""
        stmt = select(User).where(
            User.tenant_id == tenant_id, User.locked_out_at.is_not(None)
        )
        result = await self.db.execute(stmt)
        return len(result.scalars().all())


__all__ = ["TenantContextRepository"]
