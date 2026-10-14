"""
Service layer for the identity module.
"""
from __future__ import annotations

from typing import List, Optional
from uuid import UUID

from app.modules.identity.models import Tenant, User
from app.modules.identity.repository import TenantRepository, UserRepository
from app.modules.identity.schemas import TenantCreate, TenantUpdate, UserCreate, UserUpdate
from app.core.exceptions import NotFoundError, ConflictError
from app.core.audit import AuditService
from app.core.interfaces import IDatabaseService


class TenantService:
    """Service for tenant entities."""
    
    def __init__(
        self, 
        tenant_repository: TenantRepository,
        audit_service: AuditService | None = None,
        db_service: IDatabaseService | None = None
    ):
        self.tenant_repository = tenant_repository
        self._audit_service = audit_service
        self._db_service = db_service
    
    async def _record_audit(
        self,
        action: str,
        resource: str,
        resource_id: str | None = None,
        description: str | None = None,
        before_state: dict[str, Any] | None = None,
        after_state: dict[str, Any] | None = None,
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
            except Exception as exc:
                # Don't let audit failures break the main operation
                import logging
                logger = logging.getLogger(__name__)
                logger.error(f"Failed to record audit event: {exc}")

    async def get(self, id: UUID) -> Tenant:
        """Get a tenant by ID."""
        tenant = await self.tenant_repository.get(id)
        if not tenant:
            raise NotFoundError(f"Tenant with ID {id} not found")
        
        await self._record_audit(
            action="tenant.view",
            resource="tenant",
            resource_id=str(id),
            description=f"Retrieved tenant {id}",
            tenant_id=tenant.id,
        )
        
        return tenant
    
    async def get_by_name(self, name: str) -> Tenant:
        """Get a tenant by name."""
        tenant = await self.tenant_repository.get_by_name(name)
        if not tenant:
            raise NotFoundError(f"Tenant with name '{name}' not found")
        
        await self._record_audit(
            action="tenant.view_by_name",
            resource="tenant",
            resource_id=str(tenant.id),
            description=f"Retrieved tenant by name '{name}'",
            tenant_id=tenant.id,
        )
        
        return tenant
    
    async def get_multi(
        self, 
        skip: int = 0, 
        limit: int = 100
    ) -> List[Tenant]:
        """Get multiple tenants."""
        tenants = await self.tenant_repository.get_multi(skip=skip, limit=limit)
        
        await self._record_audit(
            action="tenant.list",
            resource="tenant",
            description=f"Listed {len(tenants)} tenants",
        )
        
        return tenants
    
    async def create(self, obj_in: TenantCreate, actor_user_id: UUID | None = None) -> Tenant:
        """Create a new tenant."""
        # Check for duplicate name
        existing = await self.tenant_repository.get_by_name(obj_in.name)
        if existing:
            raise ConflictError(f"Tenant with name '{obj_in.name}' already exists")
        
        tenant = await self.tenant_repository.create(obj_in)
        
        await self._record_audit(
            action="tenant.create",
            resource="tenant",
            resource_id=str(tenant.id),
            description=f"Created tenant '{tenant.name}'",
            before_state=None,
            after_state={
                "id": str(tenant.id),
                "name": tenant.name,
                "description": tenant.description,
                "is_active": tenant.is_active,
                "created_at": tenant.created_at.isoformat() if tenant.created_at else None,
                "updated_at": tenant.updated_at.isoformat() if tenant.updated_at else None,
            },
            tenant_id=tenant.id,
            actor_user_id=actor_user_id,
        )
        
        return tenant
    
    async def update(
        self, 
        id: UUID, 
        obj_in: TenantUpdate,
        actor_user_id: UUID | None = None
    ) -> Tenant:
        """Update a tenant."""
        # Get the existing tenant
        tenant = await self.tenant_repository.get(id)
        if not tenant:
            raise NotFoundError(f"Tenant with ID {id} not found")
        
        # Check for duplicate name if name is being updated
        if obj_in.name and obj_in.name != tenant.name:
            existing = await self.tenant_repository.get_by_name(obj_in.name)
            if existing:
                raise ConflictError(f"Tenant with name '{obj_in.name}' already exists")
        
        # Store before state for audit
        before_state = {
            "id": str(tenant.id),
            "name": tenant.name,
            "description": tenant.description,
            "is_active": tenant.is_active,
            "created_at": tenant.created_at.isoformat() if tenant.created_at else None,
            "updated_at": tenant.updated_at.isoformat() if tenant.updated_at else None,
        }
        
        # Update the tenant
        updated_tenant = await self.tenant_repository.update(tenant, obj_in)
        
        await self._record_audit(
            action="tenant.update",
            resource="tenant",
            resource_id=str(id),
            description=f"Updated tenant {id}",
            before_state=before_state,
            after_state={
                "id": str(updated_tenant.id),
                "name": updated_tenant.name,
                "description": updated_tenant.description,
                "is_active": updated_tenant.is_active,
                "created_at": updated_tenant.created_at.isoformat() if updated_tenant.created_at else None,
                "updated_at": updated_tenant.updated_at.isoformat() if updated_tenant.updated_at else None,
            },
            tenant_id=updated_tenant.id,
            actor_user_id=actor_user_id,
        )
        
        return updated_tenant
    
    async def delete(
        self, 
        id: UUID,
        actor_user_id: UUID | None = None
    ) -> bool:
        """Delete a tenant."""
        # Get the existing tenant
        tenant = await self.tenant_repository.get(id)
        if not tenant:
            raise NotFoundError(f"Tenant with ID {id} not found")
        
        # Store before state for audit
        before_state = {
            "id": str(tenant.id),
            "name": tenant.name,
            "description": tenant.description,
            "is_active": tenant.is_active,
            "created_at": tenant.created_at.isoformat() if tenant.created_at else None,
            "updated_at": tenant.updated_at.isoformat() if tenant.updated_at else None,
        }
        
        # Delete the tenant
        result = await self.tenant_repository.delete(tenant)
        
        await self._record_audit(
            action="tenant.delete",
            resource="tenant",
            resource_id=str(id),
            description=f"Deleted tenant {id}",
            before_state=before_state,
            after_state=None,
            tenant_id=uuid.UUID(int=0),  # Placeholder - in reality, we might not have a tenant context after deletion
            actor_user_id=actor_user_id,
        )
        
        return result


class UserService:
    """Service for user entities."""
    
    def __init__(
        self, 
        user_repository: UserRepository,
        tenant_repository: TenantRepository,
        audit_service: AuditService | None = None,
        db_service: IDatabaseService | None = None
    ):
        self.user_repository = user_repository
        self.tenant_repository = tenant_repository
        self._audit_service = audit_service
        self._db_service = db_service
    
    async def _record_audit(
        self,
        action: str,
        resource: str,
        resource_id: str | None = None,
        description: str | None = None,
        before_state: dict[str, Any] | None = None,
        after_state: dict[str, Any] | None = None,
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
            except Exception as exc:
                # Don't let audit failures break the main operation
                import logging
                logger = logging.getLogger(__name__)
                logger.error(f"Failed to record audit event: {exc}")

    async def get(self, id: UUID) -> User:
        """Get a user by ID."""
        user = await self.user_repository.get(id)
        if not user:
            raise NotFoundError(f"User with ID {id} not found")
        
        await self._record_audit(
            action="user.view",
            resource="user",
            resource_id=str(id),
            description=f"Retrieved user {id}",
            tenant_id=user.tenant_id,
        )
        
        return user
    
    async def get_by_email(self, email: str) -> User:
        """Get a user by email."""
        user = await self.user_repository.get_by_email(email)
        if not user:
            raise NotFoundError(f"User with email '{email}' not found")
        
        await self._record_audit(
            action="user.view_by_email",
            resource="user",
            resource_id=str(user.id),
            description=f"Retrieved user by email '{email}'",
            tenant_id=user.tenant_id,
        )
        
        return user
    
    async def get_multi_by_tenant(
        self, 
        tenant_id: UUID,
        skip: int = 0, 
        limit: int = 100
    ) -> List[User]:
        """Get multiple users for a tenant."""
        # Verify tenant exists
        tenant = await self.tenant_repository.get(tenant_id)
        if not tenant:
            raise NotFoundError(f"Tenant with ID {tenant_id} not found")
        
        users = await self.user_repository.get_multi_by_tenant(tenant_id, skip=skip, limit=limit)
        
        await self._record_audit(
            action="user.list",
            resource="user",
            description=f"Listed {len(users)} users for tenant {tenant_id}",
            tenant_id=tenant_id,
        )
        
        return users
    
    async def create(self, obj_in: UserCreate, tenant_id: UUID, actor_user_id: UUID | None = None) -> User:
        """Create a new user."""
        # Verify tenant exists
        tenant = await self.tenant_repository.get(tenant_id)
        if not tenant:
            raise NotFoundError(f"Tenant with ID {tenant_id} not found")
        
        # Check for duplicate email
        existing = await self.user_repository.get_by_email(obj_in.email)
        if existing:
            raise ConflictError(f"User with email '{obj_in.email}' already exists")
        
        # Hash the password (in a real implementation)
        # For now, we'll store it as-is (NOT SECURE - just for demonstration)
        # TODO: Implement proper password hashing using security.hash_password
        hashed_password = obj_in.password  # Placeholder - should be hashed
        
        user = await self.user_repository.create(
            UserCreate(
                email=obj_in.email,
                first_name=obj_in.first_name,
                last_name=obj_in.last_name,
                is_active=obj_in.is_active,
                is_superuser=obj_in.is_superuser,
                password=hashed_password  # Using hashed password
            ),
            tenant_id
        )
        
        await self._record_audit(
            action="user.create",
            resource="user",
            resource_id=str(user.id),
            description=f"Created user '{user.email}'",
            before_state=None,
            after_state={
                "id": str(user.id),
                "email": user.email,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "is_active": user.is_active,
                "is_superuser": user.is_superuser,
                "tenant_id": str(user.tenant_id),
                "created_at": user.created_at.isoformat() if user.created_at else None,
                "updated_at": user.updated_at.isoformat() if user.updated_at else None,
            },
            tenant_id=tenant_id,
            actor_user_id=actor_user_id,
        )
        
        return user
    
    async def update(
        self, 
        id: UUID, 
        obj_in: UserUpdate,
        actor_user_id: UUID | None = None
    ) -> User:
        """Update a user."""
        # Get the existing user
        user = await self.user_repository.get(id)
        if not user:
            raise NotFoundError(f"User with ID {id} not found")
        
        # Check for duplicate email if email is being updated
        if obj_in.email and obj_in.email != user.email:
            existing = await self.user_repository.get_by_email(obj_in.email)
            if existing:
                raise ConflictError(f"User with email '{obj_in.email}' already exists")
        
        # Hash the password if provided (in a real implementation)
        # For now, we'll store it as-is (NOT SECURE - just for demonstration)
        # TODO: Implement proper password hashing using security.hash_password
        update_data = obj_in.model_dump(exclude_unset=True)
        if 'password' in update_data:
            # TODO: Hash the password properly
            hashed_password = update_data['password']  # Placeholder - should be hashed
            update_data['password_hash'] = hashed_password
            del update_data['password']
        
        # Store before state for audit
        before_state = {
            "id": str(user.id),
            "email": user.email,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "is_active": user.is_active,
            "is_superuser": user.is_superuser,
            "tenant_id": str(user.tenant_id),
            "created_at": user.created_at.isoformat() if user.created_at else None,
            "updated_at": user.updated_at.isoformat() if user.updated_at else None,
        }
        
        # Update the user
        updated_user = await self.user_repository.update(user, obj_in)
        
        await self._record_audit(
            action="user.update",
            resource="user",
            resource_id=str(id),
            description=f"Updated user {id}",
            before_state=before_state,
            after_state={
                "id": str(updated_user.id),
                "email": updated_user.email,
                "first_name": updated_user.first_name,
                "last_name": updated_user.last_name,
                "is_active": updated_user.is_active,
                "is_superuser": updated_user.is_superuser,
                "tenant_id": str(updated_user.tenant_id),
                "created_at": updated_user.created_at.isoformat() if updated_user.created_at else None,
                "updated_at": updated_user.updated_at.isoformat() if updated_user.updated_at else None,
            },
            tenant_id=updated_user.tenant_id,
            actor_user_id=actor_user_id,
        )
        
        return updated_user
    
    async def delete(
        self, 
        id: UUID,
        actor_user_id: UUID | None = None
    ) -> bool:
        """Delete a user."""
        # Get the existing user
        user = await self.user_repository.get(id)
        if not user:
            raise NotFoundError(f"User with ID {id} not found")
        
        # Store before state for audit
        before_state = {
            "id": str(user.id),
            "email": user.email,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "is_active": user.is_active,
            "is_superuser": user.is_superuser,
            "tenant_id": str(user.tenant_id),
            "created_at": user.created_at.isoformat() if user.created_at else None,
            "updated_at": user.updated_at.isoformat() if user.updated_at else None,
        }
        
        # Delete the user
        result = await self.user_repository.delete(user)
        
        await self._record_audit(
            action="user.delete",
            resource="user",
            resource_id=str(id),
            description=f"Deleted user {id}",
            before_state=before_state,
            after_state=None,
            tenant_id=user.tenant_id,
            actor_user_id=actor_user_id,
        )
        
        return result


__all__ = ["TenantService", "UserService"]
