"""
Email service — factory for obtaining the configured email provider.
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


class EmailService:
    """Email service wrapper that delegates to a provider."""

    def __init__(self) -> None:
        self._provider = None
        self._initialized = False

    def _ensure_provider(self) -> None:
        """Initialize the provider if not already done."""
        if self._initialized:
            return
        from app.integrations.email.factory import get_email_provider
        from app.core.config import settings

        try:
            self._provider = get_email_provider(settings.EMAIL_PROVIDER)
            self._initialized = True
        except Exception as exc:
            logger.warning("Could not initialize email provider: %s", exc)
            self._initialized = True  # Don't retry

    async def send(self, message) -> "EmailSendResult":
        """Send an email message."""
        self._ensure_provider()
        if self._provider is None:
            # No-op fallback (log provider)
            from app.integrations.email.providers.log import LogEmailProvider

            provider = LogEmailProvider()
            self._provider = provider

        result = await self._provider.send(message)
        return result


class EmailSendResult:
    """Result of an email send operation."""

    def __init__(self, message_id: str, status: str, detail: str):
        self.message_id = message_id
        self.status = status
        self.detail = detail


def get_email_service() -> EmailService:
    """Get or create the email service singleton."""
    global _email_service
    if _email_service is None:
        _email_service = EmailService()
    return _email_service


_email_service: EmailService | None = None


__all__ = ["EmailService", "EmailSendResult", "get_email_service"]
