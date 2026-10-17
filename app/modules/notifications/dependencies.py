"""
Dependencies for the notifications module.

Provides FastAPI dependency injection for repositories and services.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import AuditService
from app.core.audit import get_core_audit_service as get_audit_service
from app.core.database import get_db
from app.core.interfaces import DatabaseService, IDatabaseService
from app.integrations.email.service import EmailService
from app.integrations.sms.service import SMSService
from app.modules.notifications.repository import NotificationRepository
from app.modules.notifications.services import NotificationService


def get_notification_repository(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> NotificationRepository:
    """Get notification repository instance."""
    return NotificationRepository(db)


def get_notification_service(
    repository: Annotated[NotificationRepository, Depends(get_notification_repository)],
    audit_service: Annotated[AuditService, Depends(get_audit_service)],
    db_service: Annotated[IDatabaseService, Depends(lambda: DatabaseService())],
    email_service: Annotated[EmailService, Depends(lambda: EmailService())],
    sms_service: Annotated[SMSService, Depends(lambda: SMSService())],
) -> NotificationService:
    """Get notification service with all dependencies injected."""
    return NotificationService(
        repository=repository,
        audit_service=audit_service,
        db_service=db_service,
        email_service=email_service,
        sms_service=sms_service,
    )


__all__ = [
    "get_notification_repository",
    "get_notification_service",
]
