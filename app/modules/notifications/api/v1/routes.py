"""
Notifications module API v1 routes.

Notification orchestration endpoints using ResponseEnvelope pattern.
"""

from __future__ import annotations

from typing import Annotated, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status

from app.core.dependencies import get_current_active_user
from app.core.exceptions import PermissionError
from app.core.security import CurrentUser
from app.models.enums import NotificationChannel, NotificationStatus, NotificationType
from app.modules.notifications.dependencies import get_notification_service
from app.modules.notifications.schemas import (
    NotificationCreate,
    NotificationListResponseEnvelope,
    NotificationPreferenceCreate,
    NotificationPreferenceListResponseEnvelope,
    NotificationPreferenceResponseEnvelope,
    NotificationPreferenceUpdate,
    NotificationResponseEnvelope,
    NotificationSendRequest,
    NotificationSendResponse,
    NotificationTemplateCreate,
    NotificationTemplateListResponseEnvelope,
    NotificationTemplateResponseEnvelope,
    NotificationTemplateUpdate,
)
from app.modules.notifications.services import NotificationService
from app.schemas.common import created, ok, paginated

router = APIRouter(
    prefix="/notifications",
    tags=["notifications"],
)


def _require_permission(current_user: CurrentUser, permission: str) -> None:
    if not current_user.has_permission(permission):
        raise PermissionError(f"Missing required permission: {permission}")


# =============================================================================
# Notification Endpoints
# =============================================================================


@router.post(
    "",
    response_model=NotificationResponseEnvelope,
    status_code=status.HTTP_201_CREATED,
)
async def create_notification(
    notification_in: NotificationCreate,
    service: Annotated[NotificationService, Depends(get_notification_service)],
    current_user: Annotated[CurrentUser, Depends(get_current_active_user)],
):
    """Create a notification (without sending)."""
    _require_permission(current_user, "notify:write")
    notification = await service.create(
        obj_in=notification_in,
        tenant_id=current_user.tenant_id,
        actor_user_id=current_user.id,
    )
    return created(data=notification, message="Notification created successfully")


@router.post(
    "/send",
    response_model=NotificationSendResponse,
    status_code=status.HTTP_200_OK,
)
async def send_notification(
    request: NotificationSendRequest,
    service: Annotated[NotificationService, Depends(get_notification_service)],
    current_user: Annotated[CurrentUser, Depends(get_current_active_user)],
):
    """Send a notification immediately through configured channels."""
    _require_permission(current_user, "notify:send")
    return await service.send(
        request=request,
        tenant_id=current_user.tenant_id,
        actor_user_id=current_user.id,
    )


@router.get(
    "",
    response_model=NotificationListResponseEnvelope,
)
async def list_notifications(
    service: Annotated[NotificationService, Depends(get_notification_service)],
    current_user: Annotated[CurrentUser, Depends(get_current_active_user)],
    type: Optional[NotificationType] = Query(
        None, description="Filter by notification type"
    ),
    status_filter: Optional[NotificationStatus] = Query(
        None, alias="status", description="Filter by delivery status"
    ),
    recipient_user_id: Optional[UUID] = Query(
        None, description="Filter by recipient user ID"
    ),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
):
    """List notifications for the current tenant."""
    _require_permission(current_user, "notify:read")
    notifications = await service.get_multi(
        tenant_id=current_user.tenant_id,
        type=type,
        status=status_filter,
        recipient_user_id=recipient_user_id,
        skip=skip,
        limit=limit,
    )
    total = await service.count(
        tenant_id=current_user.tenant_id,
        type=type,
        status=status_filter,
        recipient_user_id=recipient_user_id,
    )
    return paginated(
        items=notifications,
        total=total,
        page=(skip // limit) + 1,
        page_size=limit,
        message="Notifications retrieved successfully",
    )


@router.get(
    "/{notification_id}",
    response_model=NotificationResponseEnvelope,
)
async def get_notification(
    notification_id: UUID,
    service: Annotated[NotificationService, Depends(get_notification_service)],
    current_user: Annotated[CurrentUser, Depends(get_current_active_user)],
):
    """Get a specific notification."""
    _require_permission(current_user, "notify:read")
    return await service.get(
        id=notification_id,
        tenant_id=current_user.tenant_id,
    )


@router.get(
    "/{notification_id}/deliveries",
    response_model=dict,
)
async def get_notification_deliveries(
    notification_id: UUID,
    service: Annotated[NotificationService, Depends(get_notification_service)],
    current_user: Annotated[CurrentUser, Depends(get_current_active_user)],
):
    """Get delivery records for a notification."""
    _require_permission(current_user, "notify:read")
    deliveries = await service.get_deliveries(
        notification_id=notification_id,
        tenant_id=current_user.tenant_id,
    )
    return ok(data=deliveries, message="Deliveries retrieved successfully")


@router.delete(
    "/{notification_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_notification(
    notification_id: UUID,
    service: Annotated[NotificationService, Depends(get_notification_service)],
    current_user: Annotated[CurrentUser, Depends(get_current_active_user)],
):
    """Delete a notification."""
    _require_permission(current_user, "notify:write")
    await service.delete(
        id=notification_id,
        tenant_id=current_user.tenant_id,
        actor_user_id=current_user.id,
    )


# =============================================================================
# Template Endpoints
# =============================================================================


@router.post(
    "/templates",
    response_model=NotificationTemplateResponseEnvelope,
    status_code=status.HTTP_201_CREATED,
)
async def create_template(
    template_in: NotificationTemplateCreate,
    service: Annotated[NotificationService, Depends(get_notification_service)],
    current_user: Annotated[CurrentUser, Depends(get_current_active_user)],
):
    """Create a notification template."""
    _require_permission(current_user, "notify:templates")
    template = await service.create_template(
        obj_in=template_in,
        tenant_id=current_user.tenant_id,
        actor_user_id=current_user.id,
    )
    return created(data=template, message="Template created successfully")


@router.get(
    "/templates",
    response_model=NotificationTemplateListResponseEnvelope,
)
async def list_templates(
    service: Annotated[NotificationService, Depends(get_notification_service)],
    current_user: Annotated[CurrentUser, Depends(get_current_active_user)],
    channel: Optional[NotificationChannel] = Query(
        None, description="Filter by channel"
    ),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
):
    """List notification templates for the current tenant."""
    _require_permission(current_user, "notify:read")
    templates = await service.get_multi_templates(
        tenant_id=current_user.tenant_id,
        channel=channel,
        is_active=is_active,
        skip=skip,
        limit=limit,
    )
    return ok(data=templates, message="Templates retrieved successfully")


@router.get(
    "/templates/{template_id}",
    response_model=NotificationTemplateResponseEnvelope,
)
async def get_template(
    template_id: UUID,
    service: Annotated[NotificationService, Depends(get_notification_service)],
    current_user: Annotated[CurrentUser, Depends(get_current_active_user)],
):
    """Get a specific notification template."""
    _require_permission(current_user, "notify:read")
    return await service.get_template(
        id=template_id,
        tenant_id=current_user.tenant_id,
    )


@router.put(
    "/templates/{template_id}",
    response_model=NotificationTemplateResponseEnvelope,
)
async def update_template(
    template_id: UUID,
    template_in: NotificationTemplateUpdate,
    service: Annotated[NotificationService, Depends(get_notification_service)],
    current_user: Annotated[CurrentUser, Depends(get_current_active_user)],
):
    """Update a notification template."""
    _require_permission(current_user, "notify:templates")
    return await service.update_template(
        id=template_id,
        obj_in=template_in,
        tenant_id=current_user.tenant_id,
        actor_user_id=current_user.id,
    )


@router.delete(
    "/templates/{template_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_template(
    template_id: UUID,
    service: Annotated[NotificationService, Depends(get_notification_service)],
    current_user: Annotated[CurrentUser, Depends(get_current_active_user)],
):
    """Delete a notification template."""
    _require_permission(current_user, "notify:templates")
    await service.delete_template(
        id=template_id,
        tenant_id=current_user.tenant_id,
        actor_user_id=current_user.id,
    )


# =============================================================================
# Preference Endpoints
# =============================================================================


@router.post(
    "/preferences",
    response_model=NotificationPreferenceResponseEnvelope,
    status_code=status.HTTP_201_CREATED,
)
async def create_preference(
    preference_in: NotificationPreferenceCreate,
    service: Annotated[NotificationService, Depends(get_notification_service)],
    current_user: Annotated[CurrentUser, Depends(get_current_active_user)],
):
    """Create a notification preference."""
    _require_permission(current_user, "notify:write")
    preference = await service.create_preference(
        obj_in=preference_in,
        tenant_id=current_user.tenant_id,
        actor_user_id=current_user.id,
    )
    return created(data=preference, message="Preference created successfully")


@router.get(
    "/preferences",
    response_model=NotificationPreferenceListResponseEnvelope,
)
async def list_preferences(
    service: Annotated[NotificationService, Depends(get_notification_service)],
    current_user: Annotated[CurrentUser, Depends(get_current_active_user)],
    user_id: Optional[UUID] = Query(None, description="Filter by user ID"),
    channel: Optional[NotificationChannel] = Query(
        None, description="Filter by channel"
    ),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
):
    """List notification preferences for the current tenant."""
    _require_permission(current_user, "notify:read")
    preferences = await service.get_multi_preferences(
        tenant_id=current_user.tenant_id,
        user_id=user_id,
        channel=channel,
        skip=skip,
        limit=limit,
    )
    return ok(data=preferences, message="Preferences retrieved successfully")


@router.patch(
    "/preferences/{user_id}/{channel}",
    response_model=NotificationPreferenceResponseEnvelope,
)
async def update_preference(
    user_id: UUID,
    channel: NotificationChannel,
    preference_in: NotificationPreferenceUpdate,
    service: Annotated[NotificationService, Depends(get_notification_service)],
    current_user: Annotated[CurrentUser, Depends(get_current_active_user)],
    notification_type: Optional[NotificationType] = Query(
        None, description="Notification type filter"
    ),
):
    """Update a notification preference."""
    _require_permission(current_user, "notify:write")
    return await service.update_preference(
        user_id=user_id,
        channel=channel,
        obj_in=preference_in,
        tenant_id=current_user.tenant_id,
        notification_type=notification_type,
        actor_user_id=current_user.id,
    )


__all__ = ["router"]
