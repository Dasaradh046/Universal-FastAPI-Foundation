"""
Tests for the Brevo email provider adapter.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from httpx import Response

from app.integrations.email.contracts import (
    EmailAddress,
    EmailMessage,
)
from app.integrations.email.providers.brevo import BrevoEmailSender


@pytest.fixture
def brevo_sender():
    """Create a BrevoEmailSender with a test API key."""
    with patch("app.integrations.email.providers.brevo.settings") as mock_settings:
        mock_settings.BREVO_API_KEY = "test-brevo-api-key"
        mock_settings.BREVO_API_URL = "https://api.brevo.com/v3/smtp/email"
        return BrevoEmailSender()


@pytest.fixture
def email_message():
    """Create a test email message."""
    return EmailMessage(
        subject="Test Subject",
        html_content="<h1>Hello</h1>",
        text_content="Hello",
        from_email=EmailAddress(email="sender@example.com", name="Sender"),
        to_emails=[EmailAddress(email="recipient@example.com", name="Recipient")],
    )


class TestBrevoEmailSender:
    """Tests for the BrevoEmailSender."""

    def test_sender_initialization(self, brevo_sender):
        """BrevoEmailSender initializes with API key and URL."""
        assert brevo_sender.api_key == "test-brevo-api-key"
        assert "brevo.com" in brevo_sender.api_url

    def test_sender_requires_api_key(self):
        """BrevoEmailSender raises ValueError when API key is missing."""
        with patch("app.integrations.email.providers.brevo.settings") as mock_settings:
            mock_settings.BREVO_API_KEY = None
            mock_settings.BREVO_API_URL = "https://api.brevo.com/v3/smtp/email"
            with pytest.raises(ValueError, match="BREVO_API_KEY must be configured"):
                BrevoEmailSender()

    @pytest.mark.asyncio
    async def test_send_email_success(self, brevo_sender, email_message):
        """Successful Brevo API call returns EmailSendResult."""
        mock_response = Response(200, json={"messageId": "brevo-msg-12345"})
        mock_response.raise_for_status = lambda: None

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                return_value=mock_response
            )

            result = await brevo_sender.send(email_message)

            assert result is not None
            assert result.message_id == "brevo-msg-12345"
            assert result.status == "sent"
            assert result.provider_response["provider"] == "brevo"

    @pytest.mark.asyncio
    async def test_send_email_http_error(self, brevo_sender, email_message):
        """Brevo API HTTP error raises EmailSendError."""
        mock_response = Response(400, text="Bad request")
        mock_response.raise_for_status = lambda: (_ for _ in ()).throw(
            Exception("400 Bad Request")
        )

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                return_value=mock_response
            )

            from app.integrations.email.contracts import EmailSendError

            with pytest.raises(EmailSendError):
                await brevo_sender.send(email_message)

    def test_map_recipient(self, brevo_sender):
        """Recipient mapping produces correct Brevo format."""
        addr = EmailAddress(email="test@example.com", name="Test User")
        result = brevo_sender._map_recipient(addr)
        assert result == {"email": "test@example.com", "name": "Test User"}

    def test_map_sender(self, brevo_sender):
        """Sender mapping produces correct Brevo format."""
        addr = EmailAddress(email="test@example.com", name="Test User")
        result = brevo_sender._map_sender(addr)
        assert result == {"email": "test@example.com", "name": "Test User"}


__all__ = []
