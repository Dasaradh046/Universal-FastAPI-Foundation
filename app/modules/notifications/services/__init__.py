"""
Service layer for the notifications module.

Orchestrates notification delivery through email and SMS provider adapters,
with templates, preferences, idempotency, delivery tracking, and retry handling.
"""

from __future__ import annotations

import asyncio
import json
import logging
import string
from datetime import UTC, datetime
from typing import Any, Optional
from uuid import UUID

from app.core.audit import AuditService
from app.core.exceptions import ConflictError, NotFoundError, ValidationError
from app.core.interfaces import IDatabaseService
from app.integrations.email.contracts import EmailAddress
from app.integrations.email.service import EmailService
from app.integrations.sms.service import SMSService
from app.models.enums import (
    AuditAction,
    NotificationChannel,
    NotificationStatus,
    NotificationType,
)
from app.models.notification import (
    Notification,
    NotificationDelivery,
)
from app.modules.notifications.events import (
    NotificationCreated,
    NotificationFailed,
    NotificationSent,
    PreferenceUpdated,
    TemplateCreated,
)
from app.modules.notifications.repositories import NotificationRepository
from app.modules.notifications.schemas import (
    NotificationCreate,
    NotificationPreferenceCreate,
    NotificationPreferenceResponse,
    NotificationPreferenceUpdate,
    NotificationResponse,
    NotificationSendRequest,
    NotificationSendResponse,
    NotificationTemplateCreate,
    NotificationTemplateResponse,
    NotificationTemplateUpdate,
)


class NotificationService:
    """Service for notification orchestration.

    Routes notifications through email and SMS provider adapters with
    template rendering, preference checking, delivery tracking, idempotency,
    and retry handling.
    """

    def __init__(
        self,
        repository: NotificationRepository,
        audit_service: Optional[AuditService] = None,
        db_service: Optional[IDatabaseService] = None,
        email_service: Optional[EmailService] = None,
        sms_service: Optional[SMSService] = None,
    ):
        self.repository = repository
        self._audit_service = audit_service
        self._db_service = db_service
        self._email_service = email_service
        self._sms_service = sms_service
        self._events: list = []
        self._logger = logging.getLogger(__name__)

    def _publish_event(self, event) -> None:
        """Queue a domain event (in-process event bus placeholder)."""
        self._events.append(event)

    async def _record_audit(
        self,
        action: AuditAction,
        resource: str,
        resource_id: Optional[str] = None,
        description: Optional[str] = None,
        tenant_id: Optional[UUID] = None,
        actor_user_id: Optional[UUID] = None,
        before_state: Optional[dict] = None,
        after_state: Optional[dict] = None,
    ) -> None:
        """Record an audit event if audit service is available."""
        if self._audit_service and tenant_id:
            try:
                await self._audit_service.record_audit(
                    tenant_id=tenant_id,
                    action=action,
                    resource=resource,
                    resource_id=resource_id,
                    description=description,
                    before_state=before_state,
                    after_state=after_state,
                    actor_user_id=actor_user_id,
                )
            except Exception as exc:
                self._logger.error("Failed to record audit event: %s", exc)

    # ---- Template rendering ----

    def _render_template(self, template: str, data: Optional[dict[str, Any]]) -> str:
        """Render a template string with $placeholder substitution."""
        if not data:
            return template
        try:
            return string.Template(template).safe_substitute(data)
        except Exception:
            return template

    def _render_template_dict(
        self,
        template_data: Optional[dict[str, Any]],
    ) -> dict[str, Any]:
        """Render all string values in a template data dict."""
        if not template_data:
            return {}
        rendered: dict[str, Any] = {}
        for key, value in template_data.items():
            if isinstance(value, str):
                rendered[key] = string.Template(value).safe_substitute(template_data)
            else:
                rendered[key] = value
        return rendered

    # ---- Channel parsing ----

    @staticmethod
    def _parse_channels(channels: str) -> list[NotificationChannel]:
        """Parse a comma-separated channel string into NotificationChannel enums."""
        result: list[NotificationChannel] = []
        for part in channels.split(","):
            part = part.strip().lower()
            try:
                result.append(NotificationChannel(part))
            except ValueError:
                continue
        return result or [NotificationChannel.EMAIL]

    # ---- Preference checking ----

    async def _is_channel_enabled(
        self,
        tenant_id: UUID,
        user_id: UUID,
        channel: NotificationChannel,
        notification_type: Optional[NotificationType] = None,
    ) -> bool:
        """Check if a channel is enabled for a user, considering preferences."""
        preference = await self.repository.get_preference(
            user_id=user_id,
            channel=channel,
            notification_type=notification_type,
        )
        if preference is None:
            # No explicit preference: default to enabled
            return True
        return preference.enabled

    # ---- Notification creation ----

    async def create(
        self,
        obj_in: NotificationCreate,
        tenant_id: UUID,
        actor_user_id: Optional[UUID] = None,
    ) -> NotificationResponse:
        """Create a notification (without sending)."""
        # Check idempotency
        if obj_in.idempotency_key:
            existing = await self.repository.get_by_idempotency_key(
                obj_in.idempotency_key, tenant_id
            )
            if existing:
                raise ConflictError(
                    f"A notification with idempotency key "
                    f"'{obj_in.idempotency_key}' already exists"
                )

        notification = await self.repository.create(obj_in, tenant_id)

        await self._record_audit(
            action=AuditAction.CREATE,
            resource="notification",
            resource_id=str(notification.id),
            description=f"Created notification '{notification.type.value}'",
            after_state={
                "type": notification.type.value,
                "subject": notification.subject,
                "channels": notification.channels,
            },
            tenant_id=tenant_id,
            actor_user_id=actor_user_id,
        )
        self._publish_event(
            NotificationCreated(
                notification_id=notification.id,
                tenant_id=tenant_id,
                type=notification.type.value,
                channels=notification.channels,
                created_at=notification.created_at or datetime.now(UTC),
            )
        )

        return NotificationResponse.model_validate(notification)

    # ---- Send notification ----

    async def send(
        self,
        request: NotificationSendRequest,
        tenant_id: UUID,
        actor_user_id: Optional[UUID] = None,
    ) -> NotificationSendResponse:
        """Create and immediately send a notification through configured channels."""
        # Check idempotency
        if request.idempotency_key:
            existing = await self.repository.get_by_idempotency_key(
                request.idempotency_key, tenant_id
            )
            if existing:
                deliveries = await self.repository.get_deliveries_for_notification(
                    existing.id
                )
                return NotificationSendResponse(
                    notification_id=existing.id,
                    status="already_sent",
                    message="Notification already sent (idempotent)",
                    deliveries=[self._delivery_to_dict(d) for d in deliveries],
                )

        # Create the notification
        create_in = NotificationCreate(
            type=request.type,
            subject=request.subject,
            body=request.body,
            template_id=request.template_id,
            template_data=request.template_data,
            recipient_user_id=request.recipient_user_id,
            recipient_email=request.recipient_email,
            recipient_phone=request.recipient_phone,
            channels=request.channels,
            idempotency_key=request.idempotency_key,
            scheduled_at=None,
            expires_at=None,
            max_retries=3,
        )
        notification = await self.repository.create(create_in, tenant_id)

        # Determine recipient
        user_id = request.recipient_user_id
        email = request.recipient_email
        phone = request.recipient_phone

        # If user_id provided but no email/phone, we'd need to look up the user
        # For now, require at least one contact method
        if not email and not phone and not user_id:
            raise ValidationError(
                "At least one of recipient_user_id, "
                "recipient_email, or recipient_phone is required"
            )

        # Parse channels
        channels = self._parse_channels(request.channels)

        # Render template data
        rendered_data = self._render_template_dict(request.template_data)
        rendered_body = self._render_template(request.body, rendered_data)
        rendered_subject = (
            self._render_template(request.subject, rendered_data)
            if request.subject
            else None
        )

        # Send through each enabled channel
        delivery_results: list[dict[str, Any]] = []
        send_tasks: list = []

        for channel in channels:
            # Check user preference if user_id is available
            if user_id and not await self._is_channel_enabled(
                tenant_id, user_id, channel, request.type
            ):
                continue

            delivery = await self.repository.create_delivery(
                notification_id=notification.id,
                tenant_id=tenant_id,
                channel=channel,
            )

            if channel == NotificationChannel.EMAIL:
                task = self._send_email(
                    delivery,
                    notification,
                    rendered_subject,
                    rendered_body,
                    email,
                    tenant_id,
                )
            elif channel == NotificationChannel.SMS:
                task = self._send_sms(
                    delivery, notification, rendered_body, phone, tenant_id
                )
            else:
                # Push and in-app: mark as sent (placeholder for future adapters)
                task = self._mark_delivery_sent(delivery, channel, tenant_id)

            send_tasks.append(task)

        # Execute all channel sends concurrently
        if send_tasks:
            await asyncio.gather(*send_tasks, return_exceptions=True)

        # Fetch updated deliveries
        deliveries = await self.repository.get_deliveries_for_notification(
            notification.id
        )

        await self._record_audit(
            action=AuditAction.UPDATE,
            resource="notification",
            resource_id=str(notification.id),
            description=(
                f"Sent notification '{notification.type.value}' through "
                f"{len(channels)} channel(s)"
            ),
            tenant_id=tenant_id,
            actor_user_id=actor_user_id,
        )

        return NotificationSendResponse(
            notification_id=notification.id,
            status="sent",
            message=(
                f"Notification sent through "
                f"{len(delivery_results) + len(send_tasks)} channel(s)"
            ),
            deliveries=[self._delivery_to_dict(d) for d in deliveries],
        )

    # ---- Channel send implementations ----

    async def _send_email(
        self,
        delivery: NotificationDelivery,
        notification: Notification,
        rendered_subject: Optional[str],
        rendered_body: str,
        email: Optional[str],
        tenant_id: UUID,
    ) -> None:
        """Send a notification through the email channel."""
        if not self._email_service:
            await self.repository.update_delivery_status(
                delivery.id,
                NotificationStatus.FAILED,
                error_code="no_provider",
                error_message="Email service not configured",
            )
            return

        if not email:
            await self.repository.update_delivery_status(
                delivery.id,
                NotificationStatus.FAILED,
                error_code="no_recipient",
                error_message="No recipient email address",
            )
            return

        try:
            from_email = EmailAddress(
                email="notifications@example.com",
                name="Universal FastAPI Foundation",
            )
            result = await self._email_service.send_email(
                subject=rendered_subject or notification.type.value,
                from_email=from_email,
                to_emails=[EmailAddress(email=email)],
                text_content=rendered_body,
            )

            await self.repository.update_delivery_status(
                delivery.id,
                NotificationStatus.SENT,
                provider_message_id=result.message_id,
                provider_response=json.dumps(result.provider_response)
                if result.provider_response
                else None,
                sent_at=datetime.now(UTC),
            )

            self._publish_event(
                NotificationSent(
                    notification_id=notification.id,
                    tenant_id=tenant_id,
                    channel="email",
                    provider_message_id=result.message_id,
                )
            )
        except Exception as exc:
            self._logger.error("Email delivery failed: %s", exc)
            await self.repository.update_delivery_status(
                delivery.id,
                NotificationStatus.FAILED,
                error_code="provider_error",
                error_message=str(exc),
            )
            self._publish_event(
                NotificationFailed(
                    notification_id=notification.id,
                    tenant_id=tenant_id,
                    channel="email",
                    error_code="provider_error",
                    error_message=str(exc),
                )
            )

    async def _send_sms(
        self,
        delivery: NotificationDelivery,
        notification: Notification,
        rendered_body: str,
        phone: Optional[str],
        tenant_id: UUID,
    ) -> None:
        """Send a notification through the SMS channel."""
        if not self._sms_service:
            await self.repository.update_delivery_status(
                delivery.id,
                NotificationStatus.FAILED,
                error_code="no_provider",
                error_message="SMS service not configured",
            )
            return

        if not phone:
            await self.repository.update_delivery_status(
                delivery.id,
                NotificationStatus.FAILED,
                error_code="no_recipient",
                error_message="No recipient phone number",
            )
            return

        try:
            result = await self._sms_service.send_sms(
                to=phone,
                body=rendered_body,
            )

            await self.repository.update_delivery_status(
                delivery.id,
                NotificationStatus.SENT,
                provider_message_id=result.message_id,
                provider_response=json.dumps(result.provider_response)
                if result.provider_response
                else None,
                sent_at=datetime.now(UTC),
            )

            self._publish_event(
                NotificationSent(
                    notification_id=notification.id,
                    tenant_id=tenant_id,
                    channel="sms",
                    provider_message_id=result.message_id,
                )
            )
        except Exception as exc:
            self._logger.error("SMS delivery failed: %s", exc)
            await self.repository.update_delivery_status(
                delivery.id,
                NotificationStatus.FAILED,
                error_code="provider_error",
                error_message=str(exc),
            )
            self._publish_event(
                NotificationFailed(
                    notification_id=notification.id,
                    tenant_id=tenant_id,
                    channel="sms",
                    error_code="provider_error",
                    error_message=str(exc),
                )
            )

    async def _mark_delivery_sent(
        self,
        delivery: NotificationDelivery,
        channel: NotificationChannel,
        tenant_id: UUID,
    ) -> None:
        """Mark a push/in-app delivery as sent (placeholder for future adapters)."""
        await self.repository.update_delivery_status(
            delivery.id,
            NotificationStatus.SENT,
            sent_at=datetime.now(UTC),
        )

    # ---- Query operations ----

    async def get(self, id: UUID, tenant_id: UUID) -> NotificationResponse:
        """Get a notification by ID within a tenant."""
        notification = await self.repository.get(id)
        if not notification or notification.tenant_id != tenant_id:
            raise NotFoundError(
                f"Notification with ID {id} not found in tenant {tenant_id}"
            )

        response = NotificationResponse.model_validate(notification)
        return response

    async def get_multi(
        self,
        tenant_id: UUID,
        skip: int = 0,
        limit: int = 100,
        type: Optional[NotificationType] = None,
        status: Optional[NotificationStatus] = None,
        recipient_user_id: Optional[UUID] = None,
    ) -> list[NotificationResponse]:
        """Get multiple notifications for a tenant."""
        notifications = await self.repository.get_multi(
            tenant_id,
            skip=skip,
            limit=limit,
            type=type,
            status=status,
            recipient_user_id=recipient_user_id,
        )
        return [NotificationResponse.model_validate(n) for n in notifications]

    async def count(
        self,
        tenant_id: UUID,
        type: Optional[NotificationType] = None,
        status: Optional[NotificationStatus] = None,
        recipient_user_id: Optional[UUID] = None,
    ) -> int:
        """Count notifications for a tenant."""
        return await self.repository.count(
            tenant_id, type=type, status=status, recipient_user_id=recipient_user_id
        )

    async def get_deliveries(
        self,
        notification_id: UUID,
        tenant_id: UUID,
    ) -> list[dict[str, Any]]:
        """Get delivery records for a notification."""
        notification = await self.repository.get(notification_id)
        if not notification or notification.tenant_id != tenant_id:
            raise NotFoundError(f"Notification with ID {notification_id} not found")

        deliveries = await self.repository.get_deliveries_for_notification(
            notification_id
        )
        return [self._delivery_to_dict(d) for d in deliveries]

    @staticmethod
    def _delivery_to_dict(delivery: NotificationDelivery) -> dict[str, Any]:
        return {
            "id": str(delivery.id),
            "channel": delivery.channel.value,
            "status": delivery.status.value,
            "provider_message_id": delivery.provider_message_id,
            "error_code": delivery.error_code,
            "error_message": delivery.error_message,
            "sent_at": delivery.sent_at.isoformat() if delivery.sent_at else None,
            "delivered_at": delivery.delivered_at.isoformat()
            if delivery.delivered_at
            else None,
            "retry_count": delivery.retry_count,
            "created_at": delivery.created_at.isoformat()
            if delivery.created_at
            else None,
        }

    # ---- Template operations ----

    async def create_template(
        self,
        obj_in: NotificationTemplateCreate,
        tenant_id: UUID,
        actor_user_id: Optional[UUID] = None,
    ) -> NotificationTemplateResponse:
        """Create a notification template."""
        existing = await self.repository.get_template_by_code(tenant_id, obj_in.code)
        if existing:
            raise ConflictError(f"Template with code '{obj_in.code}' already exists")

        template = await self.repository.create_template(obj_in, tenant_id)

        await self._record_audit(
            action=AuditAction.CREATE,
            resource="notification_template",
            resource_id=str(template.id),
            description=f"Created template '{template.code}'",
            tenant_id=tenant_id,
            actor_user_id=actor_user_id,
        )
        self._publish_event(
            TemplateCreated(
                template_id=template.id,
                tenant_id=tenant_id,
                code=template.code,
                channel=template.channel.value,
                created_at=template.created_at or datetime.now(UTC),
            )
        )

        return NotificationTemplateResponse.model_validate(template)

    async def get_template(
        self, id: UUID, tenant_id: UUID
    ) -> NotificationTemplateResponse:
        """Get a template by ID within a tenant."""
        template = await self.repository.get_template(id)
        if not template or template.tenant_id != tenant_id:
            raise NotFoundError(f"Template with ID {id} not found")
        return NotificationTemplateResponse.model_validate(template)

    async def get_multi_templates(
        self,
        tenant_id: UUID,
        skip: int = 0,
        limit: int = 100,
        channel: Optional[NotificationChannel] = None,
        is_active: Optional[bool] = None,
    ) -> list[NotificationTemplateResponse]:
        """Get multiple templates for a tenant."""
        templates = await self.repository.get_multi_templates(
            tenant_id, skip=skip, limit=limit, channel=channel, is_active=is_active
        )
        return [NotificationTemplateResponse.model_validate(t) for t in templates]

    async def update_template(
        self,
        id: UUID,
        obj_in: NotificationTemplateUpdate,
        tenant_id: UUID,
        actor_user_id: Optional[UUID] = None,
    ) -> NotificationTemplateResponse:
        """Update a template."""
        template = await self.repository.get_template(id)
        if not template or template.tenant_id != tenant_id:
            raise NotFoundError(f"Template with ID {id} not found")

        updated = await self.repository.update_template(template, obj_in)

        await self._record_audit(
            action=AuditAction.UPDATE,
            resource="notification_template",
            resource_id=str(id),
            description=f"Updated template '{updated.code}'",
            tenant_id=tenant_id,
            actor_user_id=actor_user_id,
        )
        return NotificationTemplateResponse.model_validate(updated)

    async def delete_template(
        self,
        id: UUID,
        tenant_id: UUID,
        actor_user_id: Optional[UUID] = None,
    ) -> bool:
        """Delete a template."""
        template = await self.repository.get_template(id)
        if not template or template.tenant_id != tenant_id:
            raise NotFoundError(f"Template with ID {id} not found")

        result = await self.repository.delete_template(template)

        await self._record_audit(
            action=AuditAction.DELETE,
            resource="notification_template",
            resource_id=str(id),
            description=f"Deleted template '{template.code}'",
            tenant_id=tenant_id,
            actor_user_id=actor_user_id,
        )
        return result

    # ---- Preference operations ----

    async def create_preference(
        self,
        obj_in: NotificationPreferenceCreate,
        tenant_id: UUID,
        actor_user_id: Optional[UUID] = None,
    ) -> NotificationPreferenceResponse:
        """Create a notification preference."""
        existing = await self.repository.get_preference(
            user_id=obj_in.user_id,
            channel=obj_in.channel,
            notification_type=obj_in.notification_type,
        )
        if existing:
            raise ConflictError(
                f"Preference already exists for user "
                f"{obj_in.user_id} on channel {obj_in.channel.value}"
            )

        preference = await self.repository.create_preference(obj_in, tenant_id)

        await self._record_audit(
            action=AuditAction.CREATE,
            resource="notification_preference",
            resource_id=str(preference.id),
            description=(
                f"Set {obj_in.channel.value} preference to "
                f"{obj_in.enabled} for user {obj_in.user_id}"
            ),
            tenant_id=tenant_id,
            actor_user_id=actor_user_id,
        )
        self._publish_event(
            PreferenceUpdated(
                user_id=obj_in.user_id,
                tenant_id=tenant_id,
                channel=obj_in.channel.value,
                enabled=obj_in.enabled,
            )
        )

        return NotificationPreferenceResponse.model_validate(preference)

    async def get_multi_preferences(
        self,
        tenant_id: UUID,
        skip: int = 0,
        limit: int = 100,
        user_id: Optional[UUID] = None,
        channel: Optional[NotificationChannel] = None,
    ) -> list[NotificationPreferenceResponse]:
        """Get multiple preferences for a tenant."""
        preferences = await self.repository.get_multi_preferences(
            tenant_id, skip=skip, limit=limit, user_id=user_id, channel=channel
        )
        return [NotificationPreferenceResponse.model_validate(p) for p in preferences]

    async def update_preference(
        self,
        user_id: UUID,
        channel: NotificationChannel,
        obj_in: NotificationPreferenceUpdate,
        tenant_id: UUID,
        notification_type: Optional[NotificationType] = None,
        actor_user_id: Optional[UUID] = None,
    ) -> NotificationPreferenceResponse:
        """Update a notification preference."""
        preference = await self.repository.get_preference(
            user_id=user_id, channel=channel, notification_type=notification_type
        )
        if not preference:
            raise NotFoundError(
                f"Preference not found for user {user_id} on channel {channel.value}"
            )

        updated = await self.repository.update_preference(preference, obj_in)

        await self._record_audit(
            action=AuditAction.UPDATE,
            resource="notification_preference",
            resource_id=str(updated.id),
            description=f"Updated {channel.value} preference for user {user_id}",
            tenant_id=tenant_id,
            actor_user_id=actor_user_id,
        )
        self._publish_event(
            PreferenceUpdated(
                user_id=user_id,
                tenant_id=tenant_id,
                channel=channel.value,
                enabled=updated.enabled,
            )
        )

        return NotificationPreferenceResponse.model_validate(updated)

    # ---- Delete ----

    async def delete(
        self,
        id: UUID,
        tenant_id: UUID,
        actor_user_id: Optional[UUID] = None,
    ) -> bool:
        """Delete a notification."""
        notification = await self.repository.get(id)
        if not notification or notification.tenant_id != tenant_id:
            raise NotFoundError(f"Notification with ID {id} not found")

        result = await self.repository.delete(notification)

        await self._record_audit(
            action=AuditAction.DELETE,
            resource="notification",
            resource_id=str(id),
            description=f"Deleted notification '{notification.type.value}'",
            tenant_id=tenant_id,
            actor_user_id=actor_user_id,
        )
        return result


__all__ = ["NotificationService"]
