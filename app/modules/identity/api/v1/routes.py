"""
Identity module API v1 routes.

Tenant and user management endpoints using ResponseEnvelope pattern.
"""

from __future__ import annotations

from typing import List, Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status
from app.modules.identity.schemas import (
    TenantCreate,
    TenantUpdate,
    TenantResponse,
    TenantResponseEnvelope,
    TenantListResponseEnvelope,
    UserCreate,
    UserUpdate,
    UserResponse,
    UserResponseEnvelope,
    UserListResponseEnvelope,
)
from app.modules.identity.services import TenantService, UserService
from app.modules.identity.dependencies import get_tenant_service, get_user_service
from app.core.dependencies import get_current_user, get_current_active_user, require_super_admin, require_platform_admin
from app.core.security import CurrentUser
from app.schemas.common import ok, paginated, created

router = APIRouter(
    prefix="/identity",
    tags=["identity"],
    dependencies=[Depends(get_current_active_user)],
)


# =============================================================================
# Tenant Endpoints
# =============================================================================

@router.post("/tenants", response_model=TenantResponseEnvelope, status_code=status.HTTP_201_CREATED)
async def create_tenant(
    tenant_in: TenantCreate,
    service: Annotated[TenantService, Depends(get_tenant_service)],
    current_user: Annotated[CurrentUser, Depends(require_platform_admin)],
):
    """Create a new tenant (platform admin only)."""
    tenant = await service.create(
        obj_in=tenant_in,
        actor_user_id=current_user.id,
    )
    return created(data=tenant, message="Tenant created successfully")


@router.get("/tenants", response_model=TenantListResponseEnvelope)
async def list_tenants(
    service: Annotated[TenantService, Depends(get_tenant_service)],
    current_user: Annotated[CurrentUser, Depends(require_platform_admin)],
    skip: int = 0,
    limit: int = 100,
):
    """List all tenants (platform admin only)."""
    tenants = await service.get_multi(skip=skip, limit=limit)
    return ok(data=tenants, message="Tenants retrieved successfully")


@router.get("/tenants/{tenant_id}", response_model=TenantResponseEnvelope)
async def get_tenant(
    tenant_id: UUID,
    service: Annotated[TenantService, Depends(get_tenant_service)],
    current_user: Annotated[CurrentUser, Depends(require_platform_admin)],
):
    """Get a specific tenant (platform admin only)."""
    tenant = await service.get(id=tenant_id)
    return ok(data=tenant, message="Tenant retrieved successfully")


@router.put("/tenants/{tenant_id}", response_model=TenantResponseEnvelope)
async def update_tenant(
    tenant_id: UUID,
    tenant_in: TenantUpdate,
    service: Annotated[TenantService, Depends(get_tenant_service)],
    current_user: Annotated[CurrentUser, Depends(require_platform_admin)],
):
    """Update a tenant (platform admin only)."""
    tenant = await service.update(
        id=tenant_id,
        obj_in=tenant_in,
        actor_user_id=current_user.id,
    )
    return ok(data=tenant, message="Tenant updated successfully")


@router.delete("/tenants/{tenant_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_tenant(
    tenant_id: UUID,
    service: Annotated[TenantService, Depends(get_tenant_service)],
    current_user: Annotated[CurrentUser, Depends(require_platform_admin)],
):
    """Delete a tenant (platform admin only)."""
    await service.delete(id=tenant_id, actor_user_id=current_user.id)
    return None


# =============================================================================
# User Endpoints
# =============================================================================

@router.post("/tenants/{tenant_id}/users", response_model=UserResponseEnvelope, status_code=status.HTTP_201_CREATED)
async def create_user(
    tenant_id: UUID,
    user_in: UserCreate,
    service: Annotated[UserService, Depends(get_user_service)],
    current_user: Annotated[CurrentUser, Depends(get_current_active_user)],
):
    """Create a new user within a tenant."""
    # Verify tenant access
    if current_user.tenant_id != tenant_id and not current_user.is_platform_admin:
        from app.core.exceptions import PermissionError
        raise PermissionError("Not authorized to create users in this tenant")

    user = await service.create(
        obj_in=user_in,
        tenant_id=tenant_id,
        actor_user_id=current_user.id,
    )
    return created(data=user, message="User created successfully")


@router.get("/tenants/{tenant_id}/users", response_model=UserListResponseEnvelope)
async def list_users(
    tenant_id: UUID,
    service: Annotated[UserService, Depends(get_user_service)],
    current_user: Annotated[CurrentUser, Depends(get_current_active_user)],
    skip: int = 0,
    limit: int = 100,
):
    """List users within a tenant."""
    # Verify tenant access
    if current_user.tenant_id != tenant_id and not current_user.is_platform_admin:
        from app.core.exceptions import PermissionError
        raise PermissionError("Not authorized to view users in this tenant")

    users = await service.get_multi_by_tenant(tenant_id, skip=skip, limit=limit)
    return ok(data=users, message="Users retrieved successfully")


@router.get("/tenants/{tenant_id}/users/{user_id}", response_model=UserResponseEnvelope)
async def get_user(
    tenant_id: UUID,
    user_id: UUID,
    service: Annotated[UserService, Depends(get_user_service)],
    current_user: Annotated[CurrentUser, Depends(get_current_active_user)],
):
    """Get a specific user within a tenant."""
    # Verify tenant access
    if current_user.tenant_id != tenant_id and not current_user.is_platform_admin:
        from app.core.exceptions import PermissionError
        raise PermissionError("Not authorized to view users in this tenant")

    user = await service.get(id=user_id)
    # Verify user belongs to the tenant
    if user.tenant_id != tenant_id:
        from app.core.exceptions import NotFoundError
        raise NotFoundError("User not found in this tenant")

    return ok(data=user, message="User retrieved successfully")


@router.put("/tenants/{tenant_id}/users/{user_id}", response_model=UserResponseEnvelope)
async def update_user(
    tenant_id: UUID,
    user_id: UUID,
    user_in: UserUpdate,
    service: Annotated[UserService, Depends(get_user_service)],
    current_user: Annotated[CurrentUser, Depends(get_current_active_user)],
):
    """Update a user within a tenant."""
    # Verify tenant access
    if current_user.tenant_id != tenant_id and not current_user.is_platform_admin:
        from app.core.exceptions import PermissionError
        raise PermissionError("Not authorized to update users in this tenant")

    user = await service.update(
        id=user_id,
        obj_in=user_in,
        actor_user_id=current_user.id,
    )
    # Verify user belongs to the tenant
    if user.tenant_id != tenant_id:
        from app.core.exceptions import NotFoundError
        raise NotFoundError("User not found in this tenant")

    return ok(data=user, message="User updated successfully")


@router.delete("/tenants/{tenant_id}/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    tenant_id: UUID,
    user_id: UUID,
    service: Annotated[UserService, Depends(get_user_service)],
    current_user: Annotated[CurrentUser, Depends(get_current_active_user)],
):
    """Delete a user within a tenant."""
    # Verify tenant access
    if current_user.tenant_id != tenant_id and not current_user.is_platform_admin:
        from app.core.exceptions import PermissionError
        raise PermissionError("Not authorized to delete users in this tenant")

    await service.delete(id=user_id, actor_user_id=current_user.id)
    return None


__all__ = ["router"]