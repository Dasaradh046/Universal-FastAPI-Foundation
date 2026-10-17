"""
Domain events for the notifications module.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from uuid import UUID


@dataclass
class NotificationCreated:
    """Event raised when a notification is created."""

    notification_id: UUID
    tenant_id: UUID
    type: str
    channels: str
    created_at: datetime


@dataclass
class NotificationSent:
    """Event raised when a notification is sent through a channel."""

    notification_id: UUID
    tenant_id: UUID
    channel: str
    provider_message_id: Optional[str] = None


@dataclass
class NotificationFailed:
    """Event raised when a notification delivery fails."""

    notification_id: UUID
    tenant_id: UUID
    channel: str
    error_code: Optional[str]
    error_message: Optional[str]


@dataclass
class TemplateCreated:
    """Event raised when a notification template is created."""

    template_id: UUID
    tenant_id: UUID
    code: str
    channel: str
    created_at: datetime


@dataclass
class PreferenceUpdated:
    """Event raised when a user's notification preferences change."""

    user_id: UUID
    tenant_id: UUID
    channel: str
    enabled: bool


__all__ = [
    "NotificationCreated",
    "NotificationSent",
    "NotificationFailed",
    "TemplateCreated",
    "PreferenceUpdated",
]
