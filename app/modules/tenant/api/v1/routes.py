"""
Tenant module API v1 routes.

Tenant context resolution, switching, and health endpoints.
"""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status

from app.core.dependencies import get_current_active_user
from app.core.security import CurrentUser
from app.modules.tenant.dependencies import get_tenant_context_service
from app.modules.tenant.schemas import (
    TenantContextResponse,
    TenantHealthResponseEnvelope,
    TenantSwitchRequest,
    TenantSwitchResponse,
)
from app.modules.tenant.services import TenantContextService
from app.schemas.common import ok

router = APIRouter(
    prefix="/tenants",
    tags=["tenant"],
    dependencies=[Depends(get_current_active_user)],
)


@router.get("/context", response_model=TenantContextResponse)
async def get_tenant_context(
    service: Annotated[TenantContextService, Depends(get_tenant_context_service)],
    current_user: Annotated[CurrentUser, Depends()],
):
    """Get the current tenant context."""
    context = await service.resolve_context(current_user.tenant_id)
    return ok(data=context, message="Tenant context retrieved successfully")


@router.post(
    "/switch",
    response_model=TenantSwitchResponse,
    status_code=status.HTTP_200_OK,
)
async def switch_tenant(
    switch_in: TenantSwitchRequest,
    service: Annotated[TenantContextService, Depends(get_tenant_context_service)],
    current_user: Annotated[CurrentUser, Depends()],
):
    """Switch to a different tenant context."""
    context = await service.switch_context(
        tenant_id=switch_in.tenant_id,
        actor_user_id=current_user.id,
    )
    return ok(data=context, message="Tenant context switched successfully")


@router.get("/health/{tenant_id}", response_model=TenantHealthResponseEnvelope)
async def get_tenant_health(
    tenant_id: UUID,
    service: Annotated[TenantContextService, Depends(get_tenant_context_service)],
    current_user: Annotated[CurrentUser, Depends()],
):
    """Get tenant health status."""
    health = await service.get_health(tenant_id)
    return ok(data=health, message="Tenant health retrieved successfully")


__all__ = ["router"]
