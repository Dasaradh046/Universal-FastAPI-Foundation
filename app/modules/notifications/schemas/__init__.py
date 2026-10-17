"""
Pydantic schemas for the notifications module.

Follows the application-wide ResponseEnvelope pattern for consistent API responses.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional, TypeVar
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models.enums import NotificationChannel, NotificationStatus, NotificationType
from app.schemas.common import ResponseEnvelope

T = TypeVar("T")


# ---- Notification schemas ----


class NotificationBase(BaseModel):
    """Base notification model."""

    type: NotificationType = Field(
        NotificationType.INFO, description="Notification type"
    )
    subject: Optional[str] = Field(
        None, max_length=200, description="Notification subject"
    )
    body: str = Field(..., min_length=1, description="Notification body content")
    template_id: Optional[str] = Field(
        None, max_length=100, description="Template ID if using a template"
    )
    template_data: Optional[dict[str, Any]] = Field(
        None, description="Template variable data"
    )
    recipient_user_id: Optional[UUID] = Field(None, description="Recipient user ID")
    recipient_email: Optional[EmailStr] = Field(
        None, description="Recipient email address"
    )
    recipient_phone: Optional[str] = Field(
        None, max_length=32, description="Recipient phone number (E.164)"
    )
    channels: str = Field(
        "email",
        max_length=50,
        description="Comma-separated channel list (e.g. 'email,sms')",
    )
    idempotency_key: Optional[str] = Field(
        None, max_length=255, description="Idempotency key for deduplication"
    )
    scheduled_at: Optional[datetime] = Field(
        None, description="Scheduled delivery time"
    )
    expires_at: Optional[datetime] = Field(
        None, description="Expiration time for the notification"
    )
    max_retries: int = Field(3, ge=0, le=10, description="Maximum delivery retries")

    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
    )


class NotificationCreate(NotificationBase):
    """Model for creating a notification."""

    pass


class NotificationUpdate(BaseModel):
    """Model for updating a notification."""

    subject: Optional[str] = Field(None, max_length=200)
    body: Optional[str] = Field(None, min_length=1)
    channels: Optional[str] = Field(None, max_length=50)
    scheduled_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    max_retries: Optional[int] = Field(None, ge=0, le=10)

    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
    )


class NotificationInDBBase(NotificationBase):
    """Base model for notification stored in DB."""

    id: UUID
    tenant_id: UUID
    recipient_user_id: Optional[UUID] = None
    retry_count: int = 0
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class NotificationResponse(NotificationInDBBase):
    """Model for notification returned to client."""

    pass


class NotificationListResponseEnvelope(ResponseEnvelope[list[NotificationResponse]]):
    """List of notifications response envelope."""

    pass


class NotificationResponseEnvelope(ResponseEnvelope[NotificationResponse]):
    """Single notification response envelope."""

    pass


# ---- Template schemas ----


class NotificationTemplateBase(BaseModel):
    """Base notification template model."""

    code: str = Field(..., min_length=2, max_length=100, description="Template code")
    name: str = Field(..., min_length=1, max_length=200, description="Template name")
    channel: NotificationChannel = Field(..., description="Delivery channel")
    subject_template: Optional[str] = Field(
        None, max_length=200, description="Subject template"
    )
    body_template: str = Field(..., min_length=1, description="Body template")
    variables: Optional[list[str]] = Field(None, description="Template variable names")
    is_active: bool = Field(True, description="Whether the template is active")

    model_config = ConfigDict(str_strip_whitespace=True, validate_assignment=True)


class NotificationTemplateCreate(NotificationTemplateBase):
    """Model for creating a notification template."""

    pass


class NotificationTemplateUpdate(BaseModel):
    """Model for updating a notification template."""

    name: Optional[str] = Field(None, min_length=1, max_length=200)
    channel: Optional[NotificationChannel] = None
    subject_template: Optional[str] = Field(None, max_length=200)
    body_template: Optional[str] = Field(None, min_length=1)
    variables: Optional[list[str]] = None
    is_active: Optional[bool] = None

    model_config = ConfigDict(str_strip_whitespace=True, validate_assignment=True)


class NotificationTemplateResponse(NotificationTemplateBase):
    """Model for template returned to client."""

    id: UUID
    tenant_id: UUID
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class NotificationTemplateListResponseEnvelope(
    ResponseEnvelope[list[NotificationTemplateResponse]]
):
    """List of templates response envelope."""

    pass


class NotificationTemplateResponseEnvelope(
    ResponseEnvelope[NotificationTemplateResponse]
):
    """Single template response envelope."""

    pass


# ---- Preference schemas ----


class NotificationPreferenceBase(BaseModel):
    """Base notification preference model."""

    user_id: UUID = Field(..., description="User ID")
    channel: NotificationChannel = Field(..., description="Delivery channel")
    notification_type: Optional[NotificationType] = Field(
        None, description="Notification type filter"
    )
    enabled: bool = Field(
        True, description="Whether the channel is enabled for this user"
    )

    model_config = ConfigDict(str_strip_whitespace=True, validate_assignment=True)


class NotificationPreferenceCreate(NotificationPreferenceBase):
    """Model for creating a notification preference."""

    pass


class NotificationPreferenceUpdate(BaseModel):
    """Model for updating a notification preference."""

    enabled: Optional[bool] = None
    notification_type: Optional[NotificationType] = None

    model_config = ConfigDict(str_strip_whitespace=True, validate_assignment=True)


class NotificationPreferenceResponse(NotificationPreferenceBase):
    """Model for preference returned to client."""

    id: UUID
    tenant_id: UUID
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class NotificationPreferenceListResponseEnvelope(
    ResponseEnvelope[list[NotificationPreferenceResponse]]
):
    """List of preferences response envelope."""

    pass


class NotificationPreferenceResponseEnvelope(
    ResponseEnvelope[NotificationPreferenceResponse]
):
    """Single preference response envelope."""

    pass


# ---- Delivery schemas ----


class NotificationDeliveryResponse(BaseModel):
    """Model for a delivery attempt."""

    id: UUID
    channel: NotificationChannel
    status: NotificationStatus
    provider_message_id: Optional[str] = None
    error_code: Optional[str] = None
    error_message: Optional[str] = None
    sent_at: Optional[datetime] = None
    delivered_at: Optional[datetime] = None
    retry_count: int = 0
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ---- Send request schemas ----


class NotificationSendRequest(BaseModel):
    """Request to send a notification (immediate send)."""

    type: NotificationType = Field(NotificationType.INFO)
    subject: Optional[str] = Field(None, max_length=200)
    body: str = Field(..., min_length=1)
    template_id: Optional[str] = None
    template_data: Optional[dict[str, Any]] = None
    recipient_user_id: Optional[UUID] = None
    recipient_email: Optional[EmailStr] = None
    recipient_phone: Optional[str] = None
    channels: str = Field("email", max_length=50)
    idempotency_key: Optional[str] = None

    model_config = ConfigDict(str_strip_whitespace=True, validate_assignment=True)


class NotificationSendResponse(BaseModel):
    """Response for a send request."""

    notification_id: UUID
    status: str
    message: str
    deliveries: list[dict[str, Any]] = Field(default_factory=list)


__all__ = [
    "NotificationBase",
    "NotificationCreate",
    "NotificationUpdate",
    "NotificationInDBBase",
    "NotificationResponse",
    "NotificationListResponseEnvelope",
    "NotificationResponseEnvelope",
    "NotificationTemplateBase",
    "NotificationTemplateCreate",
    "NotificationTemplateUpdate",
    "NotificationTemplateResponse",
    "NotificationTemplateListResponseEnvelope",
    "NotificationTemplateResponseEnvelope",
    "NotificationPreferenceBase",
    "NotificationPreferenceCreate",
    "NotificationPreferenceUpdate",
    "NotificationPreferenceResponse",
    "NotificationPreferenceListResponseEnvelope",
    "NotificationPreferenceResponseEnvelope",
    "NotificationDeliveryResponse",
    "NotificationSendRequest",
    "NotificationSendResponse",
]
