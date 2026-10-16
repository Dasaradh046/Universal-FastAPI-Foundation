"""
Audit module API v1 routes.

Audit log querying endpoints using ResponseEnvelope pattern.
"""

from __future__ import annotations

from typing import List, Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status, Query
from app.modules.audit.schemas import (
    AuditLogCreate,
    AuditLogFilter,
    AuditLogResponse,
    AuditLogResponseEnvelope,
    AuditLogListResponseEnvelope,
)
from app.modules.audit.services import AuditServiceModule
from app.modules.audit.dependencies import get_audit_service
from app.core.dependencies import get_current_user, get_current_active_user, require_platform_admin
from app.core.security import CurrentUser
from app.schemas.common import ok, paginated

router = APIRouter(
    prefix="/audit",
    tags=["audit"],
    dependencies=[Depends(get_current_active_user)],
)


@router.get("/logs", response_model=AuditLogListResponseEnvelope)
async def list_audit_logs(
    service: Annotated[AuditServiceModule, Depends(get_audit_service)],
    current_user: Annotated[CurrentUser, Depends(require_platform_admin)],
    action: str | None = Query(None, description="Filter by action"),
    resource: str | None = Query(None, description="Filter by resource type"),
    resource_id: str | None = Query(None, description="Filter by resource ID"),
    actor_user_id: UUID | None = Query(None, description="Filter by actor user ID"),
    start_date: str | None = Query(None, description="Filter by start date (ISO format)"),
    end_date: str | None = Query(None, description="Filter by end date (ISO format)"),
    ip_address: str | None = Query(None, description="Filter by IP address"),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of records to return"),
):
    """List audit logs (platform admin only)."""
    from app.models.enums import AuditAction
    from datetime import datetime

    # Build filters
    filters = AuditLogFilter(
        action=AuditAction(action) if action else None,
        resource=resource,
        resource_id=resource_id,
        actor_user_id=actor_user_id,
        start_date=datetime.fromisoformat(start_date) if start_date else None,
        end_date=datetime.fromisoformat(end_date) if end_date else None,
        ip_address=ip_address,
    )

    logs = await service.get_logs(
        tenant_id=current_user.tenant_id,
        filters=filters,
        skip=skip,
        limit=limit,
    )

    total = await service.count_logs(
        tenant_id=current_user.tenant_id,
        filters=filters,
    )

    return paginated(
        items=logs,
        total=total,
        page=(skip // limit) + 1,
        page_size=limit,
        message="Audit logs retrieved successfully",
    )


@router.get("/logs/{log_id}", response_model=AuditLogResponseEnvelope)
async def get_audit_log(
    log_id: UUID,
    service: Annotated[AuditServiceModule, Depends(get_audit_service)],
    current_user: Annotated[CurrentUser, Depends(require_platform_admin)],
):
    """Get a specific audit log (platform admin only)."""
    log = await service.get_log(
        id=log_id,
        tenant_id=current_user.tenant_id,
    )
    return ok(data=log, message="Audit log retrieved successfully")


__all__ = ["router"]