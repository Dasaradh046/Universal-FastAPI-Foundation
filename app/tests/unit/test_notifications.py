"""
Unit tests for the notifications module.
"""

from __future__ import annotations

from app.modules.notifications.permissions import (
    NOTIFY_READ,
    NOTIFY_WRITE,
    NOTIFY_SEND,
    NOTIFY_TEMPLATES,
)
from app.modules.notifications.schemas import (
    NotificationCreate,
    NotificationUpdate,
    NotificationSendRequest,
    NotificationTemplateCreate,
    NotificationPreferenceCreate,
    NotificationChannel,
    NotificationStatus,
    NotificationType,
)
from app.modules.notifications.services import NotificationService


class TestNotificationPermissions:
    """Tests for notification permissions."""

    def test_notify_read_permission(self):
        assert NOTIFY_READ.code == "notify:read"
        assert NOTIFY_READ.name == "Read Notifications"
        assert NOTIFY_READ.module == "notifications"

    def test_notify_write_permission(self):
        assert NOTIFY_WRITE.code == "notify:write"
        assert NOTIFY_WRITE.name == "Manage Notifications"
        assert NOTIFY_WRITE.module == "notifications"

    def test_notify_send_permission(self):
        assert NOTIFY_SEND.code == "notify:send"
        assert NOTIFY_SEND.name == "Send Notifications"
        assert NOTIFY_SEND.module == "notifications"

    def test_notify_templates_permission(self):
        assert NOTIFY_TEMPLATES.code == "notify:templates"
        assert NOTIFY_TEMPLATES.name == "Manage Notification Templates"
        assert NOTIFY_TEMPLATES.module == "notifications"


class TestNotificationSchemas:
    """Tests for notification schemas."""

    def test_notification_create_defaults(self):
        n = NotificationCreate(body="Test notification body")
        assert n.body == "Test notification body"
        assert n.type == NotificationType.INFO
        assert n.channels == "email"
        assert n.max_retries == 3
        assert n.subject is None
        assert n.recipient_email is None

    def test_notification_create_full(self):
        from uuid import uuid4
        n = NotificationCreate(
            type=NotificationType.WARNING,
            subject="Warning",
            body="Disk space low",
            recipient_email="user@example.com",
            recipient_phone="+14155552671",
            channels="email,sms",
            idempotency_key="key-123",
            max_retries=5,
        )
        assert n.type == NotificationType.WARNING
        assert n.subject == "Warning"
        assert n.channels == "email,sms"
        assert n.max_retries == 5

    def test_notification_update_partial(self):
        u = NotificationUpdate(subject="New subject")
        assert u.subject == "New subject"
        assert u.body is None
        assert u.channels is None

    def test_notification_send_request(self):
        r = NotificationSendRequest(body="Send this")
        assert r.body == "Send this"
        assert r.channels == "email"

    def test_template_create(self):
        t = NotificationTemplateCreate(
            code="welcome_email",
            name="Welcome Email",
            channel=NotificationChannel.EMAIL,
            body_template="Hello $name, welcome to $app!",
            variables=["name", "app"],
        )
        assert t.code == "welcome_email"
        assert t.channel == NotificationChannel.EMAIL
        assert t.is_active is True

    def test_preference_create(self):
        from uuid import uuid4
        p = NotificationPreferenceCreate(
            user_id=uuid4(),
            channel=NotificationChannel.SMS,
            enabled=True,
        )
        assert p.channel == NotificationChannel.SMS
        assert p.enabled is True


class TestTemplateRendering:
    """Tests for template variable substitution."""

    def test_render_simple_template(self):
        service = NotificationService.__new__(NotificationService)
        result = service._render_template("Hello $name!", {"name": "World"})
        assert result == "Hello World!"

    def test_render_template_no_data(self):
        service = NotificationService.__new__(NotificationService)
        result = service._render_template("Hello $name!", None)
        assert result == "Hello $name!"

    def test_render_template_missing_var(self):
        service = NotificationService.__new__(NotificationService)
        result = service._render_template("Hello $name, $missing!", {"name": "World"})
        assert result == "Hello World, $missing!"

    def test_render_template_dict(self):
        service = NotificationService.__new__(NotificationService)
        data = {"name": "World", "count": 42}
        result = service._render_template_dict({"greeting": "Hi $name", "count_val": 42, **data})
        assert result["greeting"] == "Hi World"
        assert result["count_val"] == 42


class TestChannelParsing:
    """Tests for channel string parsing."""

    def test_parse_channels_email_only(self):
        service = NotificationService.__new__(NotificationService)
        result = service._parse_channels("email")
        assert result == [NotificationChannel.EMAIL]

    def test_parse_channels_email_sms(self):
        service = NotificationService.__new__(NotificationService)
        result = service._parse_channels("email,sms")
        assert NotificationChannel.EMAIL in result
        assert NotificationChannel.SMS in result

    def test_parse_channels_invalid_ignored(self):
        service = NotificationService.__new__(NotificationService)
        result = service._parse_channels("email,invalid_channel")
        assert result == [NotificationChannel.EMAIL]

    def test_parse_channels_empty_defaults_to_email(self):
        service = NotificationService.__new__(NotificationService)
        result = service._parse_channels("")
        assert result == [NotificationChannel.EMAIL]


class TestModuleManifest:
    """Tests for the notifications module manifest."""

    def test_manifest_exists(self):
        from app.modules.notifications import MANIFEST
        assert MANIFEST.id == "notifications"
        assert MANIFEST.version == "1.0.0"
        assert MANIFEST.name == "Notifications Module"
        assert "auth" in MANIFEST.dependencies
        assert "identity" in MANIFEST.dependencies

    def test_manifest_permissions(self):
        from app.modules.notifications import MANIFEST
        perm_codes = [p.code for p in MANIFEST.permissions]
        assert "notify:read" in perm_codes
        assert "notify:write" in perm_codes
        assert "notify:send" in perm_codes
        assert "notify:templates" in perm_codes


class TestNotificationServiceConstruction:
    """Tests for NotificationService construction and basic methods."""

    def test_service_constructs_with_repository_only(self):
        from app.modules.notifications.repository import NotificationRepository
        repo = NotificationRepository.__new__(NotificationRepository)
        service = NotificationService(repository=repo)
        assert service.repository is repo
        assert service._email_service is None
        assert service._sms_service is None

    def test_service_constructs_with_all_deps(self):
        from app.modules.notifications.repository import NotificationRepository
        repo = NotificationRepository.__new__(NotificationRepository)
        service = NotificationService(
            repository=repo,
            email_service="email",
            sms_service="sms",
        )
        assert service._email_service == "email"
        assert service._sms_service == "sms"
