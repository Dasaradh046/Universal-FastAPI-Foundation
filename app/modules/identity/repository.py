"""
Repository for the identity module.
"""
from __future__ import annotations

from typing import List, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.modules.identity.models import Tenant, User
from app.modules.identity.schemas import TenantCreate, TenantUpdate, UserCreate, UserUpdate


class TenantRepository:
    """Repository for tenant entities."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def get(self, id: UUID) -> Optional[Tenant]:
        """Get a tenant by ID."""
        result = await self.db.execute(select(Tenant).where(Tenant.id == id))
        return result.scalar_one_or_none()
    
    async def get_by_name(self, name: str) -> Optional[Tenant]:
        """Get a tenant by name."""
        result = await self.db.execute(select(Tenant).where(Tenant.name == name))
        return result.scalar_one_or_none()
    
    async def get_multi(
        self, 
        skip: int = 0, 
        limit: int = 100
    ) -> List[Tenant]:
        """Get multiple tenants."""
        result = await self.db.execute(
            select(Tenant).offset(skip).limit(limit)
        )
        return result.scalars().all()
    
    async def create(self, obj_in: TenantCreate) -> Tenant:
        """Create a new tenant."""
        db_obj = Tenant(
            name=obj_in.name,
            description=obj_in.description
        )
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
        update_data = obj_in.model_dump(exclude_unset=True)
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


class UserRepository:
    """Repository for user entities."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def get(self, id: UUID) -> Optional[User]:
        """Get a user by ID."""
        result = await self.db.execute(select(User).where(User.id == id))
        return result.scalar_one_or_none()
    
    async def get_by_email(self, email: str) -> Optional[User]:
        """Get a user by email."""
        result = await self.db.execute(select(User).where(User.email == email))
        return result.scalar_one_or_none()
    
    async def get_multi_by_tenant(
        self, 
        tenant_id: UUID,
        skip: int = 0, 
        limit: int = 100
    ) -> List[User]:
        """Get multiple users for a tenant."""
        result = await self.db.execute(
            select(User)
            .where(User.tenant_id == tenant_id)
            .offset(skip)
            .limit(limit)
        )
        return result.scalars().all()
    
    async def create(self, obj_in: UserCreate, tenant_id: UUID) -> User:
        """Create a new user."""
        # In a real implementation, we would hash the password here
        # For now, we'll store it as-is (NOT SECURE - just for demonstration)
        db_obj = User(
            email=obj_in.email,
            first_name=obj_in.first_name,
            last_name=obj_in.last_name,
            is_active=obj_in.is_active if obj_in.is_active is not None else True,
            is_superuser=obj_in.is_superuser if obj_in.is_superuser is not None else False,
            password_hash=obj_in.password,  # TODO: Hash this properly
            tenant_id=tenant_id
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
        update_data = obj_in.model_dump(exclude_unset=True)
        # Handle password separately if provided
        if 'password' in update_data:
            # TODO: Hash the password properly
            db_obj.password_hash = update_data.pop('password')
        
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


__all__ = ["TenantRepository", "UserRepository"]
