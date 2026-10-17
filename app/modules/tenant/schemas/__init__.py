"""
Tenant module schemas.

Pydantic schemas for tenant context resolution, switching, and health.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.common import ResponseEnvelope


class TenantContext(BaseModel):
    """Current tenant context for a request."""

    tenant_id: UUID
    tenant_name: str
    tenant_slug: str
    status: str
    plan: Optional[str] = None
    is_platform: bool = False
    user_count: int = 0
    active_user_count: int = 0
    created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class TenantSwitchRequest(BaseModel):
    """Request to switch tenant context."""

    tenant_id: UUID = Field(..., description="Tenant ID to switch to")

    model_config = ConfigDict(str_strip_whitespace=True)


class TenantHealthResponse(BaseModel):
    """Tenant health status."""

    tenant_id: UUID
    status: str
    healthy: bool
    active_users: int
    total_users: int
    mfa_enabled_users: int
    locked_users: int
    message: str

    model_config = ConfigDict(from_attributes=True)


class TenantContextResponse(ResponseEnvelope[TenantContext]):
    """Single tenant context response envelope."""
    pass


class TenantSwitchResponse(ResponseEnvelope[TenantContext]):
    """Tenant switch response envelope."""
    pass


class TenantHealthResponseEnvelope(ResponseEnvelope[TenantHealthResponse]):
    """Tenant health response envelope."""
    pass


__all__ = [
    "TenantContext",
    "TenantSwitchRequest",
    "TenantHealthResponse",
    "TenantContextResponse",
    "TenantSwitchResponse",
    "TenantHealthResponseEnvelope",
]
