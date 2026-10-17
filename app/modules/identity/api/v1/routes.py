"""
Identity module API v1 routes.

Tenant and user management endpoints using ResponseEnvelope pattern.
"""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status

from app.core.exceptions import PermissionError
from app.core.security import (
    CurrentUser,
    get_current_active_user,
    require_platform_admin,
)
from app.models.enums import Role
from app.modules.identity.dependencies import (
    get_role_service,
    get_tenant_service,
    get_user_service,
)
from app.modules.identity.schemas import (
    RoleCreate,
    RoleListResponseEnvelope,
    RolePermissionAssign,
    RolePermissionListResponse,
    RoleResponseEnvelope,
    RoleUpdate,
    TenantCreate,
    TenantListResponseEnvelope,
    TenantResponseEnvelope,
    TenantSettings,
    TenantStatsResponseEnvelope,
    TenantStatusUpdate,
    TenantUpdate,
    UserBulkStatusUpdate,
    UserCreate,
    UserListResponseEnvelope,
    UserPasswordReset,
    UserResponseEnvelope,
    UserStatusUpdate,
    UserUpdate,
)
from app.modules.identity.services import RoleService, TenantService, UserService
from app.schemas.common import created, ok

router = APIRouter(
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


# =============================================================================
# Role Endpoints
# =============================================================================

@router.post("/tenants/{tenant_id}/roles", response_model=RoleResponseEnvelope, status_code=status.HTTP_201_CREATED)
async def create_role(
    tenant_id: UUID,
    role_in: RoleCreate,
    service: Annotated[RoleService, Depends(get_role_service)],
    current_user: Annotated[CurrentUser, Depends(get_current_active_user)],
):
    """Create a new role within a tenant."""
    if current_user.tenant_id != tenant_id and not current_user.is_platform_admin:
        from app.core.exceptions import PermissionError
        raise PermissionError("Not authorized to create roles in this tenant")

    role = await service.create(
        obj_in=role_in,
        tenant_id=tenant_id,
        actor_user_id=current_user.id,
    )
    return created(data=role, message="Role created successfully")


@router.get("/tenants/{tenant_id}/roles", response_model=RoleListResponseEnvelope)
async def list_roles(
    tenant_id: UUID,
    service: Annotated[RoleService, Depends(get_role_service)],
    current_user: Annotated[CurrentUser, Depends(get_current_active_user)],
    skip: int = 0,
    limit: int = 100,
):
    """List roles within a tenant."""
    if current_user.tenant_id != tenant_id and not current_user.is_platform_admin:
        from app.core.exceptions import PermissionError
        raise PermissionError("Not authorized to view roles in this tenant")

    roles = await service.get_multi_by_tenant(tenant_id, skip=skip, limit=limit)
    return ok(data=roles, message="Roles retrieved successfully")


@router.get("/tenants/{tenant_id}/roles/{role_id}", response_model=RoleResponseEnvelope)
async def get_role(
    tenant_id: UUID,
    role_id: UUID,
    service: Annotated[RoleService, Depends(get_role_service)],
    current_user: Annotated[CurrentUser, Depends(get_current_active_user)],
):
    """Get a specific role within a tenant."""
    if current_user.tenant_id != tenant_id and not current_user.is_platform_admin:
        from app.core.exceptions import PermissionError
        raise PermissionError("Not authorized to view roles in this tenant")

    role = await service.get(id=role_id)
    if role.tenant_id != tenant_id:
        from app.core.exceptions import NotFoundError
        raise NotFoundError("Role not found in this tenant")
    return ok(data=role, message="Role retrieved successfully")


@router.put("/tenants/{tenant_id}/roles/{role_id}", response_model=RoleResponseEnvelope)
async def update_role(
    tenant_id: UUID,
    role_id: UUID,
    role_in: RoleUpdate,
    service: Annotated[RoleService, Depends(get_role_service)],
    current_user: Annotated[CurrentUser, Depends(get_current_active_user)],
):
    """Update a role within a tenant."""
    if current_user.tenant_id != tenant_id and not current_user.is_platform_admin:
        from app.core.exceptions import PermissionError
        raise PermissionError("Not authorized to update roles in this tenant")

    role = await service.update(
        id=role_id,
        obj_in=role_in,
        actor_user_id=current_user.id,
    )
    if role.tenant_id != tenant_id:
        from app.core.exceptions import NotFoundError
        raise NotFoundError("Role not found in this tenant")
    return ok(data=role, message="Role updated successfully")


@router.delete("/tenants/{tenant_id}/roles/{role_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_role(
    tenant_id: UUID,
    role_id: UUID,
    service: Annotated[RoleService, Depends(get_role_service)],
    current_user: Annotated[CurrentUser, Depends(get_current_active_user)],
):
    """Delete a role within a tenant."""
    if current_user.tenant_id != tenant_id and not current_user.is_platform_admin:
        from app.core.exceptions import PermissionError
        raise PermissionError("Not authorized to delete roles in this tenant")

    await service.delete(id=role_id, actor_user_id=current_user.id)


@router.get("/tenants/{tenant_id}/roles/{role_id}/permissions", response_model=RoleResponseEnvelope)
async def list_role_permissions(
    tenant_id: UUID,
    role_id: UUID,
    service: Annotated[RoleService, Depends(get_role_service)],
    current_user: Annotated[CurrentUser, Depends(get_current_active_user)],
):
    """List permissions assigned to a role."""
    if current_user.tenant_id != tenant_id and not current_user.is_platform_admin:
        from app.core.exceptions import PermissionError
        raise PermissionError("Not authorized to view roles in this tenant")

    permissions = await service.list_permissions(role_id)
    return ok(
        data={"role_id": str(role_id), "permissions": [p.model_dump() for p in permissions]},
        message="Permissions retrieved successfully",
    )


@router.post(
    "/tenants/{tenant_id}/roles/{role_id}/permissions",
    response_model=RolePermissionListResponse,
)
async def assign_role_permissions(
    tenant_id: UUID,
    role_id: UUID,
    permissions_in: RolePermissionAssign,
    service: Annotated[RoleService, Depends(get_role_service)],
    current_user: Annotated[CurrentUser, Depends(get_current_active_user)],
):
    """Assign permissions to a role."""
    if current_user.tenant_id != tenant_id and not current_user.is_platform_admin:
        raise PermissionError("Not authorized to manage roles in this tenant")

    result = await service.assign_permissions(
        role_id=role_id,
        permissions=permissions_in.permissions,
        actor_user_id=current_user.id,
    )
    return ok(data=result, message="Permissions assigned successfully")


@router.delete(
    "/tenants/{tenant_id}/roles/{role_id}/permissions",
    response_model=RolePermissionListResponse,
)
async def revoke_role_permissions(
    tenant_id: UUID,
    role_id: UUID,
    permissions_in: RolePermissionAssign,
    service: Annotated[RoleService, Depends(get_role_service)],
    current_user: Annotated[CurrentUser, Depends(get_current_active_user)],
):
    """Revoke permissions from a role."""
    if current_user.tenant_id != tenant_id and not current_user.is_platform_admin:
        raise PermissionError("Not authorized to manage roles in this tenant")

    result = await service.revoke_permissions(
        role_id=role_id,
        permissions=permissions_in.permissions,
        actor_user_id=current_user.id,
    )
    return ok(data=result, message="Permissions revoked successfully")


@router.get(
    "/tenants/{tenant_id}/roles/{role_id}/users",
    response_model=UserResponseEnvelope,
)
async def list_role_users(
    tenant_id: UUID,
    role_id: UUID,
    service: Annotated[RoleService, Depends(get_role_service)],
    current_user: Annotated[CurrentUser, Depends(get_current_active_user)],
):
    """List users assigned to a role."""
    if current_user.tenant_id != tenant_id and not current_user.is_platform_admin:
        raise PermissionError("Not authorized to view roles in this tenant")

    users = await service.list_users(role_id)
    return ok(
        data={"role_id": str(role_id), "users": users},
        message="Users retrieved successfully",
    )


@router.post(
    "/tenants/{tenant_id}/roles/{role_id}/activate",
    response_model=RoleResponseEnvelope,
)
async def activate_role(
    tenant_id: UUID,
    role_id: UUID,
    service: Annotated[RoleService, Depends(get_role_service)],
    current_user: Annotated[CurrentUser, Depends(get_current_active_user)],
):
    """Activate a tenant role."""
    if current_user.tenant_id != tenant_id and not current_user.is_platform_admin:
        raise PermissionError("Not authorized to manage roles in this tenant")

    role = await service.set_active(id=role_id, is_active=True, actor_user_id=current_user.id)
    return ok(data=role, message="Role activated successfully")


@router.post(
    "/tenants/{tenant_id}/roles/{role_id}/deactivate",
    response_model=RoleResponseEnvelope,
)
async def deactivate_role(
    tenant_id: UUID,
    role_id: UUID,
    service: Annotated[RoleService, Depends(get_role_service)],
    current_user: Annotated[CurrentUser, Depends(get_current_active_user)],
):
    """Deactivate a tenant role."""
    if current_user.tenant_id != tenant_id and not current_user.is_platform_admin:
        raise PermissionError("Not authorized to manage roles in this tenant")

    role = await service.set_active(id=role_id, is_active=False, actor_user_id=current_user.id)
    return ok(data=role, message="Role deactivated successfully")


# =============================================================================
# Additional Tenant Endpoints
# =============================================================================

@router.get("/tenants/search", response_model=TenantListResponseEnvelope)
async def search_tenants(
    q: str,
    service: Annotated[TenantService, Depends(get_tenant_service)],
    current_user: Annotated[CurrentUser, Depends(require_platform_admin)],
    skip: int = 0,
    limit: int = 100,
):
    """Search tenants by name, slug, or plan (platform admin only)."""
    tenants = await service.search(query=q, skip=skip, limit=limit)
    return ok(data=tenants, message="Tenants retrieved successfully")


@router.get("/tenants/{tenant_id}/stats", response_model=TenantStatsResponseEnvelope)
async def get_tenant_stats(
    tenant_id: UUID,
    service: Annotated[TenantService, Depends(get_tenant_service)],
    current_user: Annotated[CurrentUser, Depends(require_platform_admin)],
):
    """Get tenant statistics (platform admin only)."""
    stats = await service.get_stats(id=tenant_id)
    return ok(data=stats, message="Tenant stats retrieved successfully")


@router.patch("/tenants/{tenant_id}/status", response_model=TenantResponseEnvelope)
async def update_tenant_status(
    tenant_id: UUID,
    status_in: TenantStatusUpdate,
    service: Annotated[TenantService, Depends(get_tenant_service)],
    current_user: Annotated[CurrentUser, Depends(require_platform_admin)],
):
    """Update a tenant's lifecycle status (platform admin only)."""
    tenant = await service.update_status(
        id=tenant_id,
        obj_in=status_in,
        actor_user_id=current_user.id,
    )
    return ok(data=tenant, message="Tenant status updated successfully")


@router.patch("/tenants/{tenant_id}/settings", response_model=TenantResponseEnvelope)
async def update_tenant_settings(
    tenant_id: UUID,
    settings_in: TenantSettings,
    service: Annotated[TenantService, Depends(get_tenant_service)],
    current_user: Annotated[CurrentUser, Depends(require_platform_admin)],
):
    """Update tenant settings (platform admin only)."""
    tenant = await service.update_settings(
        id=tenant_id,
        obj_in=settings_in,
        actor_user_id=current_user.id,
    )
    return ok(data=tenant, message="Tenant settings updated successfully")


@router.post("/tenants/{tenant_id}/invite", response_model=UserResponseEnvelope, status_code=status.HTTP_201_CREATED)
async def invite_user(
    tenant_id: UUID,
    user_in: UserCreate,
    service: Annotated[UserService, Depends(get_user_service)],
    current_user: Annotated[CurrentUser, Depends(get_current_active_user)],
):
    """Invite a new user within a tenant (admin only)."""
    if current_user.tenant_id != tenant_id and not current_user.is_platform_admin:
        raise PermissionError("Not authorized to invite users in this tenant")
    if not (current_user.is_platform_admin or current_user.is_super_admin
            or current_user.tenant_id == tenant_id and current_user.role.name.startswith("ADMIN")):
        raise PermissionError("Insufficient privileges to invite users")

    user = await service.invite(
        obj_in=user_in,
        tenant_id=tenant_id,
        actor_user_id=current_user.id,
    )
    return created(data=user, message="User invited successfully")


# =============================================================================
# Additional User Endpoints
# =============================================================================

@router.get("/tenants/{tenant_id}/users/search", response_model=UserListResponseEnvelope)
async def search_users(
    tenant_id: UUID,
    q: str,
    service: Annotated[UserService, Depends(get_user_service)],
    current_user: Annotated[CurrentUser, Depends(get_current_active_user)],
    skip: int = 0,
    limit: int = 100,
):
    """Search users within a tenant."""
    if current_user.tenant_id != tenant_id and not current_user.is_platform_admin:
        raise PermissionError("Not authorized to search users in this tenant")

    users = await service.search(tenant_id, q, skip=skip, limit=limit)
    return ok(data=users, message="Users retrieved successfully")


@router.get("/tenants/{tenant_id}/users/{user_id}/sessions", response_model=UserListResponseEnvelope)
async def list_user_sessions(
    tenant_id: UUID,
    user_id: UUID,
    service: Annotated[UserService, Depends(get_user_service)],
    current_user: Annotated[CurrentUser, Depends(get_current_active_user)],
):
    """Get active sessions for a user."""
    if current_user.tenant_id != tenant_id and not current_user.is_platform_admin:
        raise PermissionError("Not authorized to view user sessions in this tenant")

    sessions = await service.get_sessions(user_id=user_id)
    return ok(data=sessions, message="Sessions retrieved successfully")


@router.get("/tenants/{tenant_id}/users/stats", response_model=UserResponseEnvelope)
async def get_user_stats(
    tenant_id: UUID,
    service: Annotated[UserService, Depends(get_user_service)],
    current_user: Annotated[CurrentUser, Depends(get_current_active_user)],
):
    """Get user statistics for a tenant."""
    if current_user.tenant_id != tenant_id and not current_user.is_platform_admin:
        raise PermissionError("Not authorized to view user stats in this tenant")

    stats = await service.get_stats(tenant_id=tenant_id)
    return ok(data=stats, message="User stats retrieved successfully")


@router.patch("/tenants/{tenant_id}/users/{user_id}/status", response_model=UserResponseEnvelope)
async def update_user_status(
    tenant_id: UUID,
    user_id: UUID,
    status_in: UserStatusUpdate,
    service: Annotated[UserService, Depends(get_user_service)],
    current_user: Annotated[CurrentUser, Depends(get_current_active_user)],
):
    """Activate or deactivate a user account."""
    if current_user.tenant_id != tenant_id and not current_user.is_platform_admin:
        raise PermissionError("Not authorized to modify users in this tenant")

    user = await service.set_status(
        id=user_id,
        obj_in=status_in,
        actor_user_id=current_user.id,
    )
    return ok(data=user, message="User status updated successfully")


@router.post("/tenants/{tenant_id}/users/{user_id}/lock", response_model=UserResponseEnvelope)
async def lock_user(
    tenant_id: UUID,
    user_id: UUID,
    service: Annotated[UserService, Depends(get_user_service)],
    current_user: Annotated[CurrentUser, Depends(get_current_active_user)],
    reason: str | None = None,
):
    """Lock a user account."""
    if current_user.tenant_id != tenant_id and not current_user.is_platform_admin:
        raise PermissionError("Not authorized to lock users in this tenant")

    user = await service.lock_account(id=user_id, reason=reason, actor_user_id=current_user.id)
    return ok(data=user, message="User account locked")


@router.post("/tenants/{tenant_id}/users/{user_id}/unlock", response_model=UserResponseEnvelope)
async def unlock_user(
    tenant_id: UUID,
    user_id: UUID,
    service: Annotated[UserService, Depends(get_user_service)],
    current_user: Annotated[CurrentUser, Depends(get_current_active_user)],
):
    """Unlock a user account."""
    if current_user.tenant_id != tenant_id and not current_user.is_platform_admin:
        raise PermissionError("Not authorized to unlock users in this tenant")

    user = await service.unlock_account(id=user_id, actor_user_id=current_user.id)
    return ok(data=user, message="User account unlocked")


@router.post("/tenants/{tenant_id}/users/{user_id}/role", response_model=UserResponseEnvelope)
async def set_user_role(
    tenant_id: UUID,
    user_id: UUID,
    role: Role,
    service: Annotated[UserService, Depends(get_user_service)],
    current_user: Annotated[CurrentUser, Depends(get_current_active_user)],
):
    """Set a user's primary role."""
    if current_user.tenant_id != tenant_id and not current_user.is_platform_admin:
        raise PermissionError("Not authorized to modify users in this tenant")

    user = await service.set_role(id=user_id, role=role, actor_user_id=current_user.id)
    return ok(data=user, message="User role updated successfully")


@router.post("/tenants/{tenant_id}/users/{user_id}/mfa-requirement", response_model=UserResponseEnvelope)
async def set_user_mfa_requirement(
    tenant_id: UUID,
    user_id: UUID,
    required: bool,
    service: Annotated[UserService, Depends(get_user_service)],
    current_user: Annotated[CurrentUser, Depends(get_current_active_user)],
):
    """Set whether a user must enroll in MFA."""
    if current_user.tenant_id != tenant_id and not current_user.is_platform_admin:
        raise PermissionError("Not authorized to modify users in this tenant")

    user = await service.set_mfa_requirement(id=user_id, required=required, actor_user_id=current_user.id)
    return ok(data=user, message="MFA requirement updated successfully")


@router.post("/tenants/{tenant_id}/users/{user_id}/password-change-required", response_model=UserResponseEnvelope)
async def set_password_change_required(
    tenant_id: UUID,
    user_id: UUID,
    must_change: bool,
    service: Annotated[UserService, Depends(get_user_service)],
    current_user: Annotated[CurrentUser, Depends(get_current_active_user)],
):
    """Set whether a user must change their password on next login."""
    if current_user.tenant_id != tenant_id and not current_user.is_platform_admin:
        raise PermissionError("Not authorized to modify users in this tenant")

    user = await service.set_password_change_required(
        id=user_id, must_change=must_change, actor_user_id=current_user.id
    )
    return ok(data=user, message="Password change requirement updated successfully")


@router.post(
    "/tenants/{tenant_id}/users/{user_id}/reset-password",
    response_model=UserResponseEnvelope,
    status_code=status.HTTP_200_OK,
)
async def reset_user_password(
    tenant_id: UUID,
    user_id: UUID,
    service: Annotated[UserService, Depends(get_user_service)],
    current_user: Annotated[CurrentUser, Depends(get_current_active_user)],
    reset_in: UserPasswordReset | None = None,
):
    """Reset a user's password (admin action)."""
    if current_user.tenant_id != tenant_id and not current_user.is_platform_admin:
        raise PermissionError("Not authorized to reset passwords in this tenant")

    new_password = reset_in.new_password if reset_in else None
    result = await service.reset_password(
        id=user_id,
        new_password=new_password,
        actor_user_id=current_user.id,
    )
    return ok(
        data=result,
        message="Password reset successfully"
        + (f" Temporary password: {result.get('temporary_password')}" if result.get("temporary_password") else ""),
    )


@router.post("/tenants/{tenant_id}/users/bulk-status", response_model=UserResponseEnvelope)
async def bulk_update_user_status(
    tenant_id: UUID,
    bulk_in: UserBulkStatusUpdate,
    service: Annotated[UserService, Depends(get_user_service)],
    current_user: Annotated[CurrentUser, Depends(get_current_active_user)],
):
    """Bulk update status for multiple users."""
    if current_user.tenant_id != tenant_id and not current_user.is_platform_admin:
        raise PermissionError("Not authorized to modify users in this tenant")

    result = await service.bulk_update_status(
        tenant_id=tenant_id,
        user_ids=bulk_in.user_ids,
        is_active=bulk_in.is_active,
        mfa_enrollment_required=bulk_in.mfa_enrollment_required,
        actor_user_id=current_user.id,
    )
    return ok(data=result, message="Bulk status update completed")


# =============================================================================
# User Role Management (additional roles beyond primary)
# =============================================================================

@router.post("/tenants/{tenant_id}/users/{user_id}/roles/{role_code}", status_code=status.HTTP_204_NO_CONTENT)
async def assign_user_role(
    tenant_id: UUID,
    user_id: UUID,
    role_code: str,
    service: Annotated[UserService, Depends(get_user_service)],
    current_user: Annotated[CurrentUser, Depends(get_current_active_user)],
):
    """Assign an additional role to a user."""
    if current_user.tenant_id != tenant_id and not current_user.is_platform_admin:
        raise PermissionError("Not authorized to manage user roles in this tenant")

    await service.assign_role(
        user_id=user_id,
        role_code=role_code,
        tenant_id=tenant_id,
        actor_user_id=current_user.id,
    )


@router.delete("/tenants/{tenant_id}/users/{user_id}/roles/{role_code}", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_user_role(
    tenant_id: UUID,
    user_id: UUID,
    role_code: str,
    service: Annotated[UserService, Depends(get_user_service)],
    current_user: Annotated[CurrentUser, Depends(get_current_active_user)],
):
    """Revoke an additional role from a user."""
    if current_user.tenant_id != tenant_id and not current_user.is_platform_admin:
        raise PermissionError("Not authorized to manage user roles in this tenant")

    await service.revoke_role(
        user_id=user_id,
        role_code=role_code,
        tenant_id=tenant_id,
        actor_user_id=current_user.id,
    )


@router.get("/tenants/{tenant_id}/users/{user_id}/roles", response_model=UserListResponseEnvelope)
async def list_user_additional_roles(
    tenant_id: UUID,
    user_id: UUID,
    service: Annotated[UserService, Depends(get_user_service)],
    current_user: Annotated[CurrentUser, Depends(get_current_active_user)],
):
    """List all additional roles assigned to a user."""
    if current_user.tenant_id != tenant_id and not current_user.is_platform_admin:
        raise PermissionError("Not authorized to view user roles in this tenant")

    roles = await service.list_user_roles(user_id=user_id, tenant_id=tenant_id)
    return ok(data=roles, message="User roles retrieved successfully")


__all__ = ["router"]
