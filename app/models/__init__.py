"""
Models package — centralized SQLAlchemy model definitions.
"""

from app.models.audit import AuditLog
from app.models.base import Base, TenantBase, TimestampMixin, UUIDPrimaryKey
from app.models.enums import (
    AuditAction,
    NotificationChannel,
    NotificationStatus,
    NotificationType,
    Role,
    TenantStatus,
)
from app.models.example import Example
from app.models.notification import (
    Notification,
    NotificationDelivery,
    NotificationPreference,
    NotificationTemplate,
)
from app.models.tenant import Tenant
from app.models.user import (
    EmailVerificationToken,
    PasswordResetToken,
    Permission,
    RoleModel,
    RolePermission,
    User,
    UserRole,
    UserSession,
)

__all__ = [
    "Base",
    "UUIDPrimaryKey",
    "TimestampMixin",
    "TenantBase",
    "Tenant",
    "User",
    "RoleModel",
    "Permission",
    "RolePermission",
    "UserRole",
    "UserSession",
    "PasswordResetToken",
    "EmailVerificationToken",
    "Example",
    "AuditLog",
    "Notification",
    "NotificationTemplate",
    "NotificationPreference",
    "NotificationDelivery",
    "Role",
    "AuditAction",
    "TenantStatus",
    "NotificationChannel",
    "NotificationStatus",
    "NotificationType",
]
