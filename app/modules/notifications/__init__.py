"""
Notifications module — provider-independent notification orchestration.

Routes notifications through email, SMS, push, and in-app channels using
configurable provider adapters, with templates, preferences, delivery
tracking, idempotency, and retry handling.
"""

from __future__ import annotations

from app.modules.module_sdk import ModuleManifest
from app.modules.notifications.api.v1.routes import router as notifications_router_v1
from app.modules.notifications.permissions import (
    NOTIFY_READ,
    NOTIFY_SEND,
    NOTIFY_TEMPLATES,
    NOTIFY_WRITE,
)
from app.modules.notifications.repository import NotificationRepository
from app.modules.notifications.services import NotificationService

# Module manifest - required for registration
MANIFEST = ModuleManifest(
    id="notifications",
    version="1.0.0",
    name="Notifications Module",
    description=(
        "Provider-independent notification orchestration with templates, "
        "preferences, and delivery tracking"
    ),
    dependencies=["auth", "identity"],
    required_capabilities=[],
    optional_capabilities=["audit"],
    router=notifications_router_v1,
    models=[],  # Models live in app.models.notification
    permissions=[
        NOTIFY_READ,  # type: ignore[list-item]
        NOTIFY_WRITE,  # type: ignore[list-item]
        NOTIFY_SEND,  # type: ignore[list-item]
        NOTIFY_TEMPLATES,  # type: ignore[list-item]
    ],
)

__all__ = [
    "NotificationService",
    "NotificationRepository",
    "MANIFEST",
    "notifications_router_v1",
    "NOTIFY_READ",
    "NOTIFY_WRITE",
    "NOTIFY_SEND",
    "NOTIFY_TEMPLATES",
]
