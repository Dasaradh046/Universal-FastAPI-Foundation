"""
Notifications module — provider-independent notification orchestration.

Routes notifications through email, SMS, push, and in-app channels using
configurable provider adapters, with templates, preferences, delivery
tracking, idempotency, and retry handling.
"""

from __future__ import annotations

from app.modules.module_sdk import ModuleManifest

from .api import notifications_router_v1
from .events import (
    NotificationCreated,
    NotificationFailed,
    NotificationSent,
    PreferenceUpdated,
    TemplateCreated,
)
from .permissions import (
    NOTIFY_READ,
    NOTIFY_SEND,
    NOTIFY_TEMPLATES,
    NOTIFY_WRITE,
)
from .repositories import NotificationRepository
from .schemas import (
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
from .services import NotificationService

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
    models=[],
    permissions=[
        NOTIFY_READ,
        NOTIFY_WRITE,
        NOTIFY_SEND,
        NOTIFY_TEMPLATES,
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
    "NotificationCreate",
    "NotificationResponse",
    "NotificationSendRequest",
    "NotificationSendResponse",
    "NotificationTemplateCreate",
    "NotificationTemplateResponse",
    "NotificationTemplateUpdate",
    "NotificationPreferenceCreate",
    "NotificationPreferenceResponse",
    "NotificationPreferenceUpdate",
    "NotificationCreated",
    "NotificationSent",
    "NotificationFailed",
    "TemplateCreated",
    "PreferenceUpdated",
]
