"""
Repository for the identity module.
"""

from __future__ import annotations

from typing import List, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.encryption import encrypt_field, hash_password
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
        # Hash the password properly
        hashed_password = hash_password(obj_in.password)
        
        db_obj = User(
            email=obj_in.email,
            first_name=obj_in.first_name,
            last_name=obj_in.last_name,
            is_active=obj_in.is_active if obj_in.is_active is not None else True,
            is_superuser=obj_in.is_superuser if obj_in.is_superuser is not None else False,
            password_hash=hashed_password,  # Properly hashed password
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


__all__ = ["TenantRepository", "UserRepository"]
