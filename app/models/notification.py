"""
SQLAlchemy models for the notifications module.

Defines Notification, NotificationTemplate, NotificationPreference, and
NotificationDelivery entities for provider-independent notification orchestration.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    UUID as SQL_UUID,
)
from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TenantBase, TimestampMixin
from app.models.enums import NotificationChannel, NotificationStatus, NotificationType


class Notification(TenantBase, TimestampMixin, Base):
    """A notification to be delivered to one or more recipients.

    Orchestrates delivery across channels (email, SMS, push, in-app) via
    provider adapters. Delivery status is tracked per channel in
    NotificationDelivery rows.
    """

    __tablename__ = "notifications"

    type: Mapped[NotificationType] = mapped_column(
        Enum(NotificationType), nullable=False, index=True
    )
    subject: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    template_id: Mapped[Optional[str]] = mapped_column(
        String(100), nullable=True, index=True
    )
    template_data: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON
    recipient_user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        SQL_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    recipient_email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    recipient_phone: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    channels: Mapped[str] = mapped_column(String(50), nullable=False, default="email")
    idempotency_key: Mapped[Optional[str]] = mapped_column(
        String(255), nullable=True, index=True
    )
    scheduled_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    expires_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    max_retries: Mapped[int] = mapped_column(Integer, nullable=False, default=3)
    retry_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    deliveries: Mapped[list["NotificationDelivery"]] = relationship(
        "NotificationDelivery",
        back_populates="notification",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    actor_user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        SQL_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )


class NotificationTemplate(TenantBase, TimestampMixin, Base):
    """Reusable notification template with variable placeholders."""

    __tablename__ = "notification_templates"

    code: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    channel: Mapped[NotificationChannel] = mapped_column(
        Enum(NotificationChannel), nullable=False
    )
    subject_template: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    body_template: Mapped[str] = mapped_column(Text, nullable=False)
    variables: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True
    )  # JSON list of variable names
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    __table_args__ = (
        UniqueConstraint(
            "tenant_id", "code", name="uq_notification_templates_tenant_code"
        ),
    )


class NotificationPreference(TenantBase, TimestampMixin, Base):
    """Per-user channel preferences for notification delivery."""

    __tablename__ = "notification_preferences"

    user_id: Mapped[uuid.UUID] = mapped_column(
        SQL_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    channel: Mapped[NotificationChannel] = mapped_column(
        Enum(NotificationChannel), nullable=False
    )
    notification_type: Mapped[Optional[NotificationType]] = mapped_column(
        Enum(NotificationType), nullable=True
    )
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class NotificationDelivery(TenantBase, TimestampMixin, Base):
    """Per-channel delivery attempt and status for a notification."""

    __tablename__ = "notification_deliveries"

    notification_id: Mapped[uuid.UUID] = mapped_column(
        SQL_UUID(as_uuid=True),
        ForeignKey("notifications.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    channel: Mapped[NotificationChannel] = mapped_column(
        Enum(NotificationChannel), nullable=False
    )
    status: Mapped[NotificationStatus] = mapped_column(
        Enum(NotificationStatus),
        nullable=False,
        default=NotificationStatus.PENDING,
        index=True,
    )
    provider_message_id: Mapped[Optional[str]] = mapped_column(
        String(255), nullable=True
    )
    provider_response: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True
    )  # JSON
    error_code: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    sent_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    delivered_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    retry_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    notification: Mapped[Notification] = relationship(
        "Notification", back_populates="deliveries", lazy="selectin"
    )


__all__ = [
    "Notification",
    "NotificationTemplate",
    "NotificationPreference",
    "NotificationDelivery",
]
