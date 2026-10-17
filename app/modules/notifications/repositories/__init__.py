"""
Repository for the notifications module.

Data-access layer for Notification, NotificationTemplate, NotificationPreference,
and NotificationDelivery entities.
"""

from __future__ import annotations

from datetime import datetime
from typing import List, Optional
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import NotificationChannel, NotificationStatus, NotificationType
from app.models.notification import (
    Notification,
    NotificationDelivery,
    NotificationPreference,
    NotificationTemplate,
)
from app.modules.notifications.schemas import (
    NotificationCreate,
    NotificationPreferenceCreate,
    NotificationPreferenceUpdate,
    NotificationTemplateCreate,
    NotificationTemplateUpdate,
    NotificationUpdate,
)


class NotificationRepository:
    """Repository for notification entities."""

    def __init__(self, db: AsyncSession):
        self.db = db

    # ---- Notification lookups ----

    async def get(self, id: UUID) -> Optional[Notification]:
        """Get a notification by ID."""
        stmt = select(Notification).where(Notification.id == id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_multi(
        self,
        tenant_id: UUID,
        skip: int = 0,
        limit: int = 100,
        type: Optional[NotificationType] = None,
        status: Optional[NotificationStatus] = None,
        recipient_user_id: Optional[UUID] = None,
    ) -> List[Notification]:
        """Get multiple notifications for a tenant with optional filters."""
        stmt = select(Notification).where(Notification.tenant_id == tenant_id)

        if type:
            stmt = stmt.where(Notification.type == type)
        if status:
            stmt = stmt.where(
                Notification.id.in_(
                    select(NotificationDelivery.notification_id).where(
                        NotificationDelivery.status == status
                    )
                )
            )
        if recipient_user_id:
            stmt = stmt.where(Notification.recipient_user_id == recipient_user_id)

        stmt = stmt.order_by(Notification.created_at.desc()).offset(skip).limit(limit)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def count(
        self,
        tenant_id: UUID,
        type: Optional[NotificationType] = None,
        status: Optional[NotificationStatus] = None,
        recipient_user_id: Optional[UUID] = None,
    ) -> int:
        """Count notifications for a tenant with optional filters."""
        stmt = (
            select(func.count())
            .select_from(Notification)
            .where(Notification.tenant_id == tenant_id)
        )

        if type:
            stmt = stmt.where(Notification.type == type)
        if status:
            stmt = stmt.where(
                Notification.id.in_(
                    select(NotificationDelivery.notification_id).where(
                        NotificationDelivery.status == status
                    )
                )
            )
        if recipient_user_id:
            stmt = stmt.where(Notification.recipient_user_id == recipient_user_id)

        result = await self.db.execute(stmt)
        return int(result.scalar_one())

    async def get_by_idempotency_key(
        self,
        idempotency_key: str,
        tenant_id: UUID,
    ) -> Optional[Notification]:
        """Get a notification by idempotency key."""
        stmt = select(Notification).where(
            Notification.idempotency_key == idempotency_key,
            Notification.tenant_id == tenant_id,
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_pending_deliveries(
        self,
        limit: int = 100,
    ) -> List[NotificationDelivery]:
        """Get pending delivery attempts for retry processing."""
        stmt = (
            select(NotificationDelivery)
            .where(NotificationDelivery.status == NotificationStatus.PENDING)
            .order_by(NotificationDelivery.created_at.asc())
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    # ---- Notification mutations ----

    async def create(self, obj_in: NotificationCreate, tenant_id: UUID) -> Notification:
        """Create a new notification."""
        db_obj = Notification(
            tenant_id=tenant_id,
            type=obj_in.type,
            subject=obj_in.subject,
            body=obj_in.body,
            template_id=obj_in.template_id,
            template_data=(
                __import__("json").dumps(obj_in.template_data)
                if obj_in.template_data
                else None
            ),
            recipient_user_id=obj_in.recipient_user_id,
            recipient_email=obj_in.recipient_email,
            recipient_phone=obj_in.recipient_phone,
            channels=obj_in.channels,
            idempotency_key=obj_in.idempotency_key,
            scheduled_at=obj_in.scheduled_at,
            expires_at=obj_in.expires_at,
            max_retries=obj_in.max_retries,
        )
        self.db.add(db_obj)
        await self.db.flush()
        await self.db.refresh(db_obj)
        return db_obj

    async def update(
        self, db_obj: Notification, obj_in: NotificationUpdate
    ) -> Notification:
        """Update a notification."""
        update_data = obj_in.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_obj, field, value)
        self.db.add(db_obj)
        await self.db.flush()
        await self.db.refresh(db_obj)
        return db_obj

    async def delete(self, db_obj: Notification) -> bool:
        """Delete a notification."""
        await self.db.delete(db_obj)
        await self.db.flush()
        return True

    # ---- Delivery mutations ----

    async def create_delivery(
        self,
        notification_id: UUID,
        tenant_id: UUID,
        channel: NotificationChannel,
    ) -> NotificationDelivery:
        """Create a pending delivery record."""
        delivery = NotificationDelivery(
            tenant_id=tenant_id,
            notification_id=notification_id,
            channel=channel,
            status=NotificationStatus.PENDING,
        )
        self.db.add(delivery)
        await self.db.flush()
        await self.db.refresh(delivery)
        return delivery

    async def update_delivery_status(
        self,
        delivery_id: UUID,
        status: NotificationStatus,
        provider_message_id: Optional[str] = None,
        provider_response: Optional[str] = None,
        error_code: Optional[str] = None,
        error_message: Optional[str] = None,
        sent_at: Optional[datetime] = None,
        delivered_at: Optional[datetime] = None,
        increment_retry: bool = False,
    ) -> Optional[NotificationDelivery]:
        """Update a delivery record's status."""
        stmt = select(NotificationDelivery).where(
            NotificationDelivery.id == delivery_id
        )
        result = await self.db.execute(stmt)
        delivery = result.scalar_one_or_none()
        if not delivery:
            return None

        delivery.status = status
        if provider_message_id is not None:
            delivery.provider_message_id = provider_message_id
        if provider_response is not None:
            delivery.provider_response = provider_response
        if error_code is not None:
            delivery.error_code = error_code
        if error_message is not None:
            delivery.error_message = error_message
        if sent_at is not None:
            delivery.sent_at = sent_at
        if delivered_at is not None:
            delivery.delivered_at = delivered_at
        if increment_retry:
            delivery.retry_count += 1

        self.db.add(delivery)
        await self.db.flush()
        await self.db.refresh(delivery)
        return delivery

    async def get_deliveries_for_notification(
        self,
        notification_id: UUID,
    ) -> List[NotificationDelivery]:
        """Get all delivery records for a notification."""
        stmt = (
            select(NotificationDelivery)
            .where(NotificationDelivery.notification_id == notification_id)
            .order_by(NotificationDelivery.created_at.asc())
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    # ---- Template lookups ----

    async def get_template(self, id: UUID) -> Optional[NotificationTemplate]:
        """Get a template by ID."""
        stmt = select(NotificationTemplate).where(NotificationTemplate.id == id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_template_by_code(
        self,
        tenant_id: UUID,
        code: str,
    ) -> Optional[NotificationTemplate]:
        """Get a template by code within a tenant."""
        stmt = select(NotificationTemplate).where(
            NotificationTemplate.tenant_id == tenant_id,
            NotificationTemplate.code == code,
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_multi_templates(
        self,
        tenant_id: UUID,
        skip: int = 0,
        limit: int = 100,
        channel: Optional[NotificationChannel] = None,
        is_active: Optional[bool] = None,
    ) -> List[NotificationTemplate]:
        """Get multiple templates for a tenant."""
        stmt = select(NotificationTemplate).where(
            NotificationTemplate.tenant_id == tenant_id
        )

        if channel:
            stmt = stmt.where(NotificationTemplate.channel == channel)
        if is_active is not None:
            stmt = stmt.where(NotificationTemplate.is_active == is_active)

        stmt = (
            stmt.order_by(NotificationTemplate.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def count_templates(
        self,
        tenant_id: UUID,
        channel: Optional[NotificationChannel] = None,
        is_active: Optional[bool] = None,
    ) -> int:
        """Count templates for a tenant."""
        stmt = (
            select(func.count())
            .select_from(NotificationTemplate)
            .where(NotificationTemplate.tenant_id == tenant_id)
        )
        if channel:
            stmt = stmt.where(NotificationTemplate.channel == channel)
        if is_active is not None:
            stmt = stmt.where(NotificationTemplate.is_active == is_active)

        result = await self.db.execute(stmt)
        return int(result.scalar_one())

    async def create_template(
        self, obj_in: NotificationTemplateCreate, tenant_id: UUID
    ) -> NotificationTemplate:
        """Create a new template."""
        db_obj = NotificationTemplate(
            tenant_id=tenant_id,
            code=obj_in.code,
            name=obj_in.name,
            channel=obj_in.channel,
            subject_template=obj_in.subject_template,
            body_template=obj_in.body_template,
            variables=(
                __import__("json").dumps(obj_in.variables) if obj_in.variables else None
            ),
            is_active=obj_in.is_active,
        )
        self.db.add(db_obj)
        await self.db.flush()
        await self.db.refresh(db_obj)
        return db_obj

    async def update_template(
        self,
        db_obj: NotificationTemplate,
        obj_in: NotificationTemplateUpdate,
    ) -> NotificationTemplate:
        """Update a template."""
        update_data = obj_in.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_obj, field, value)
        self.db.add(db_obj)
        await self.db.flush()
        await self.db.refresh(db_obj)
        return db_obj

    async def delete_template(self, db_obj: NotificationTemplate) -> bool:
        """Delete a template."""
        await self.db.delete(db_obj)
        await self.db.flush()
        return True

    # ---- Preference lookups ----

    async def get_preference(
        self,
        user_id: UUID,
        channel: NotificationChannel,
        notification_type: Optional[NotificationType] = None,
    ) -> Optional[NotificationPreference]:
        """Get a user's notification preference."""
        stmt = select(NotificationPreference).where(
            NotificationPreference.user_id == user_id,
            NotificationPreference.channel == channel,
        )
        if notification_type:
            stmt = stmt.where(
                NotificationPreference.notification_type == notification_type
            )
        else:
            stmt = stmt.where(NotificationPreference.notification_type.is_(None))
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_multi_preferences(
        self,
        tenant_id: UUID,
        skip: int = 0,
        limit: int = 100,
        user_id: Optional[UUID] = None,
        channel: Optional[NotificationChannel] = None,
    ) -> List[NotificationPreference]:
        """Get multiple preferences for a tenant."""
        stmt = select(NotificationPreference).where(
            NotificationPreference.tenant_id == tenant_id
        )

        if user_id:
            stmt = stmt.where(NotificationPreference.user_id == user_id)
        if channel:
            stmt = stmt.where(NotificationPreference.channel == channel)

        stmt = (
            stmt.order_by(NotificationPreference.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def create_preference(
        self, obj_in: NotificationPreferenceCreate, tenant_id: UUID
    ) -> NotificationPreference:
        """Create a new preference."""
        db_obj = NotificationPreference(
            tenant_id=tenant_id,
            user_id=obj_in.user_id,
            channel=obj_in.channel,
            notification_type=obj_in.notification_type,
            enabled=obj_in.enabled,
        )
        self.db.add(db_obj)
        await self.db.flush()
        await self.db.refresh(db_obj)
        return db_obj

    async def update_preference(
        self,
        db_obj: NotificationPreference,
        obj_in: NotificationPreferenceUpdate,
    ) -> NotificationPreference:
        """Update a preference."""
        update_data = obj_in.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_obj, field, value)
        self.db.add(db_obj)
        await self.db.flush()
        await self.db.refresh(db_obj)
        return db_obj

    async def delete_preference(self, db_obj: NotificationPreference) -> bool:
        """Delete a preference."""
        await self.db.delete(db_obj)
        await self.db.flush()
        return True


__all__ = ["NotificationRepository"]
