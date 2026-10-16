"""
Repository for the identity module.

Data-access layer following the Repository pattern with dependency inversion.
Uses centralized models from app.models.
"""

from __future__ import annotations

from typing import List, Optional, Protocol
from uuid import UUID

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.tenant import Tenant
from app.models.user import User
from app.modules.identity.schemas import TenantCreate, TenantUpdate, UserCreate, UserUpdate


class TenantRepository:
    """Repository for tenant entities.

    Implements the data-access layer for the Tenant entity.
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get(self, id: UUID) -> Optional[Tenant]:
        """Get a tenant by ID."""
        stmt = select(Tenant).where(Tenant.id == id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_name(self, name: str) -> Optional[Tenant]:
        """Get a tenant by name."""
        stmt = select(Tenant).where(Tenant.name == name)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_multi(
        self,
        skip: int = 0,
        limit: int = 100
    ) -> List[Tenant]:
        """Get multiple tenants."""
        stmt = select(Tenant).offset(skip).limit(limit)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def create(self, obj_in: TenantCreate) -> Tenant:
        """Create a new tenant."""
        from app.core.encryption import encrypt_field

        # Extract plaintext fields for encryption
        tenant_data = obj_in.model_dump(exclude_unset=True)

        # Encrypt sensitive fields
        encrypted_fields = {}
        for field in ['billing_email', 'billing_address', 'tax_id', 'primary_contact_phone']:
            if field in tenant_data and tenant_data[field] is not None:
                encrypted_value = encrypt_field(tenant_data[field])
                encrypted_fields[f"{field}_encrypted"] = encrypted_value

        # Set defaults for settings if not provided
        if 'timezone' not in tenant_data or tenant_data['timezone'] is None:
            tenant_data['timezone'] = 'UTC'
        if 'locale' not in tenant_data or tenant_data['locale'] is None:
            tenant_data['locale'] = 'en-US'

        # Remove plaintext sensitive fields (they won't be stored)
        for field in ['billing_email', 'billing_address', 'tax_id', 'primary_contact_phone']:
            tenant_data.pop(field, None)

        # Add encrypted fields
        tenant_data.update(encrypted_fields)

        db_obj = Tenant(**tenant_data)
        self.db.add(db_obj)
        await self.db.flush()
        await self.db.refresh(db_obj)
        return db_obj

    async def update(
        self,
        db_obj: Tenant,
        obj_in: TenantUpdate
    ) -> Tenant:
        """Update a tenant."""
        from app.core.encryption import encrypt_field

        update_data = obj_in.model_dump(exclude_unset=True)

        # Encrypt sensitive fields if they are being updated
        encrypted_fields = {}
        for field in ['billing_email', 'billing_address', 'tax_id', 'primary_contact_phone']:
            if field in update_data and update_data[field] is not None:
                encrypted_value = encrypt_field(update_data[field])
                encrypted_fields[f"{field}_encrypted"] = encrypted_value
                # Remove the plaintext field from update_data
                del update_data[field]

        # Add encrypted fields to update_data
        update_data.update(encrypted_fields)

        for field, value in update_data.items():
            setattr(db_obj, field, value)
        self.db.add(db_obj)
        await self.db.flush()
        await self.db.refresh(db_obj)
        return db_obj

    async def delete(self, db_obj: Tenant) -> bool:
        """Delete a tenant."""
        await self.db.delete(db_obj)
        await self.db.flush()
        return True

    async def count(self) -> int:
        """Count total tenants."""
        stmt = select(func.count()).select_from(Tenant)
        result = await self.db.execute(stmt)
        return int(result.scalar_one())


class UserRepository:
    """Repository for user entities.

    Implements the data-access layer for the User entity.
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get(self, id: UUID) -> Optional[User]:
        """Get a user by ID."""
        stmt = select(User).where(User.id == id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_email(self, email: str) -> Optional[User]:
        """Get a user by email (global lookup)."""
        stmt = select(User).where(User.email == email)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_email_tenant(self, tenant_id: UUID, email: str) -> Optional[User]:
        """Get a user by email within a tenant."""
        stmt = select(User).where(
            User.tenant_id == tenant_id,
            User.email == email
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_multi_by_tenant(
        self,
        tenant_id: UUID,
        skip: int = 0,
        limit: int = 100
    ) -> List[User]:
        """Get multiple users for a tenant."""
        stmt = (
            select(User)
            .where(User.tenant_id == tenant_id)
            .offset(skip)
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def create(self, obj_in: UserCreate, tenant_id: UUID) -> User:
        """Create a new user."""
        from app.core.encryption import hash_password

        # Hash the password properly
        hashed_password = hash_password(obj_in.password)

        db_obj = User(
            email=obj_in.email,
            first_name=obj_in.first_name,
            last_name=obj_in.last_name,
            is_active=obj_in.is_active if obj_in.is_active is not None else True,
            is_superuser=obj_in.is_superuser if obj_in.is_superuser is not None else False,
            password_hash=hashed_password,
            tenant_id=tenant_id,
        )
        self.db.add(db_obj)
        await self.db.flush()
        await self.db.refresh(db_obj)
        return db_obj

    async def update(
        self,
        db_obj: User,
        obj_in: UserUpdate
    ) -> User:
        """Update a user."""
        from app.core.encryption import hash_password

        update_data = obj_in.model_dump(exclude_unset=True)

        # Handle password separately if provided
        if 'password' in update_data:
            # Hash the password properly
            hashed_password = hash_password(update_data['password'])
            update_data['password_hash'] = hashed_password
            del update_data['password']

        for field, value in update_data.items():
            setattr(db_obj, field, value)
        self.db.add(db_obj)
        await self.db.flush()
        await self.db.refresh(db_obj)
        return db_obj

    async def delete(self, db_obj: User) -> bool:
        """Delete a user."""
        await self.db.delete(db_obj)
        await self.db.flush()
        return True

    async def count_by_tenant(self, tenant_id: UUID) -> int:
        """Count users in a tenant."""
        stmt = select(func.count()).where(User.tenant_id == tenant_id)
        result = await self.db.execute(stmt)
        return int(result.scalar_one())


# Repository Protocols for Dependency Inversion
class TenantRepositoryProtocol(Protocol):
    """Protocol for tenant repository - enables dependency inversion."""

    async def get(self, id: UUID) -> Optional[Tenant]: ...
    async def get_by_name(self, name: str) -> Optional[Tenant]: ...
    async def get_multi(self, skip: int, limit: int) -> List[Tenant]: ...
    async def create(self, obj_in: TenantCreate) -> Tenant: ...
    async def update(self, db_obj: Tenant, obj_in: TenantUpdate) -> Tenant: ...
    async def delete(self, db_obj: Tenant) -> bool: ...
    async def count(self) -> int: ...


class UserRepositoryProtocol(Protocol):
    """Protocol for user repository - enables dependency inversion."""

    async def get(self, id: UUID) -> Optional[User]: ...
    async def get_by_email(self, email: str) -> Optional[User]: ...
    async def get_by_email_tenant(self, tenant_id: UUID, email: str) -> Optional[User]: ...
    async def get_multi_by_tenant(self, tenant_id: UUID, skip: int, limit: int) -> List[User]: ...
    async def create(self, obj_in: UserCreate, tenant_id: UUID) -> User: ...
    async def update(self, db_obj: User, obj_in: UserUpdate) -> User: ...
    async def delete(self, db_obj: User) -> bool: ...
    async def count_by_tenant(self, tenant_id: UUID) -> int: ...


__all__ = [
    "TenantRepository",
    "UserRepository",
    "TenantRepositoryProtocol",
    "UserRepositoryProtocol",
]