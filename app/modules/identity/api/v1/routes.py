"""
Identity module — tenant and user management APIs.
"""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import (
    APIRouter,
    Body,
    Depends,
    HTTPException,
    Request,
    Response,
    status,
)
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.dependencies import CurrentUser, get_current_active_user, require_permission, require_super_admin
from app.modules.identity.dependencies import get_tenant_service, get_user_service
from app.modules.identity.schemas import (
    TenantCreate,
    TenantUpdate,
    TenantResponse,
    UserCreate,
    UserUpdate,
    UserResponse,
)
from app.modules.identity.services import TenantService, UserService
from app.modules.identity.permissions import (
    TENANT_READ,
    TENANT_WRITE,
    TENANT_DELETE,
    USER_READ,
    USER_WRITE,
    USER_DELETE,
)

logger = get_logger(__name__)

router = APIRouter()


# ---- Helper functions ------------------------------------------------------ #

def _client_ip(request: Request) -> str | None:
    """Best-effort client IP extraction (respects X-Forwarded-For when behind a proxy)."""
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else None


# ---- Tenant endpoints ------------------------------------------------------ #

@router.get("/tenants", response_model=list[TenantResponse])
async def list_tenants(
    request: Request,
    skip: int = 0,
    limit: int = 100,
    session: Annotated[AsyncSession, Depends(get_db)],
    tenant_service: Annotated[TenantService, Depends(get_tenant_service)],
    current_user: Annotated[CurrentUser, Depends(get_current_active_user)],
    _: Annotated[bool, Depends(require_permission(TENANT_READ))],
):
    """List all tenants with pagination."""
    tenants = await tenant_service.get_multi(skip=skip, limit=limit)
    return tenants


@router.get("/tenants/{tenant_id}", response_model=TenantResponse)
async def get_tenant(
    tenant_id: UUID,
    session: Annotated[AsyncSession, Depends(get_db)],
    tenant_service: Annotated[TenantService, Depends(get_tenant_service)],
    current_user: Annotated[CurrentUser, Depends(get_current_active_user)],
    _: Annotated[bool, Depends(require_permission(TENANT_READ))],
):
    """Get a tenant by ID."""
    return await tenant_service.get(tenant_id)


@router.post("/tenants", response_model=TenantResponse, status_code=status.HTTP_201_CREATED)
async def create_tenant(
    request: Request,
    tenant_create: TenantCreate,
    session: Annotated[AsyncSession, Depends(get_db)],
    tenant_service: Annotated[TenantService, Depends(get_tenant_service)],
):
    """Create a new tenant."""
    ip_address = _client_ip(request)
    return await tenant_service.create(tenant_create, actor_user_id=None)  # TODO: Get from auth


@router.put("/tenants/{tenant_id}", response_model=TenantResponse)
async def update_tenant(
    tenant_id: UUID,
    tenant_update: TenantUpdate,
    session: Annotated[AsyncSession, Depends(get_db)],
    tenant_service: Annotated[TenantService, Depends(get_tenant_service]),
    current_user: Annotated[CurrentUser, Depends(get_current_active_user)],
    _: Annotated[bool, Depends(require_permission(TENANT_WRITE))],
):
    """Update an existing tenant."""
    return await tenant_service.update(tenant_id, tenant_update, actor_user_id=None)  # TODO: Get from auth


@router.delete("/tenants/{tenant_id}", response_model=dict, status_code=status.HTTP_204_NO_CONTENT)
async def delete_tenant(
    tenant_id: UUID,
    request: Request,
    session: Annotated[AsyncSession, Depends(get_db)],
    tenant_service: Annotated[TenantService, Depends(get_tenant_service)],
):
    """Delete a tenant."""
    ip_address = _client_ip(request)
    result = await tenant_service.delete(tenant_id, actor_user_id=None)  # TODO: Get from auth
    return {"success": result}


# ---- User endpoints -------------------------------------------------------- #

@router.get("/users", response_model=list[UserResponse])
async def list_users(
    request: Request,
    tenant_id: UUID | None = None,
    skip: int = 0,
    limit: int = 100,
    session: Annotated[AsyncSession, Depends(get_db)],
    user_service: Annotated[UserService, Depends(get_user_service)],
    current_user: Annotated[CurrentUser, Depends(get_current_active_user)],
    _: Annotated[bool, Depends(require_permission(USER_READ))],
):
    """List users, optionally filtered by tenant ID."""
    if tenant_id:
        users = await user_service.get_multi_by_tenant(tenant_id, skip=skip, limit=limit)
    else:
        # For now, we don't have a cross-tenant list users method in the service
        # This would need to be added to the UserService if needed
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="Listing users across all tenants not implemented"
        )
    return users


@router.get("/users/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: UUID,
    session: Annotated[AsyncSession, Depends(get_db)],
    user_service: Annotated[UserService, Depends(get_user_service)],
):
    """Get a user by ID."""
    return await user_service.get(user_id)


@router.post("/users", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    request: Request,
    user_create: UserCreate,
    tenant_id: UUID,  # This should come from auth context in a real implementation
    session: Annotated[AsyncSession, Depends(get_db)],
    user_service: Annotated[UserService, Depends(get_user_service)],
):
    """Create a new user."""
    ip_address = _client_ip(request)
    # In a real implementation, tenant_id would come from the authenticated user's context
    # For now, we require it as a parameter (this would typically be in the URL or auth context)
    return await user_service.create(user_create, tenant_id, actor_user_id=None)  # TODO: Get from auth


@router.put("/users/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: UUID,
    user_update: UserUpdate,
    session: Annotated[AsyncSession, Depends(get_db)],
    user_service: Annotated[UserService, Depends(get_user_service)],
):
    """Update an existing user."""
    return await user_service.update(user_id, user_update, actor_user_id=None)  # TODO: Get from auth


@router.delete("/users/{user_id}", response_model=dict, status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: UUID,
    request: Request,
    session: Annotated[AsyncSession, Depends(get_db)],
    user_service: Annotated[UserService, Depends(get_user_service)],
):
    """Delete a user."""
    ip_address = _client_ip(request)
    result = await user_service.delete(user_id, actor_user_id=None)  # TODO: Get from auth
    return {"success": result}


__all__ = ["router"]