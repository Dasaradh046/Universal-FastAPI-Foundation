"""
Brevo (formerly Sendinblue) transactional email provider adapter.

Implements the ``EmailSender`` protocol using Brevo's SMTP/REST API.

Brevo API reference: https://developers.brevo.com
"""

from __future__ import annotations

import httpx

from app.core.config import settings
from app.core.logging import get_logger
from app.integrations.email.contracts import (
    EmailAddress,
    EmailMessage,
    EmailSender,
    EmailSendError,
    EmailSendResult,
)

logger = get_logger(__name__)

BREVO_API_URL = "https://api.brevo.com/v3/smtp/email"


class BrevoEmailSender(EmailSender):
    """Brevo transactional email sender implementation."""

    def __init__(self):
        self.api_key = settings.BREVO_API_KEY
        self.api_url = settings.BREVO_API_URL or BREVO_API_URL

        if not self.api_key:
            raise ValueError("BREVO_API_KEY must be configured for the Brevo provider")

    def _map_recipient(self, addr: EmailAddress) -> dict[str, str]:
        """Map an EmailAddress to a Brevo recipient object."""
        return {"email": addr.email, "name": addr.name or ""}

    def _map_sender(self, addr: EmailAddress) -> dict[str, str]:
        """Map an EmailAddress to a Brevo sender object."""
        return {"email": addr.email, "name": addr.name or ""}

    async def send(self, message: EmailMessage) -> EmailSendResult:
        """Send an email via Brevo's transactional email API.

        Args:
            message: The email message to send

        Returns:
            Result of the send operation

        Raises:
            EmailSendError: If the email could not be sent
        """
        payload: dict[str, object] = {
            "sender": self._map_sender(message.from_email),
            "to": [self._map_recipient(addr) for addr in message.to_emails],
            "subject": message.subject,
        }

        if message.html_content:
            payload["htmlContent"] = message.html_content
        if message.text_content:
            payload["textContent"] = message.text_content

        if message.cc_emails:
            payload["cc"] = [self._map_recipient(addr) for addr in message.cc_emails]
        if message.bcc_emails:
            payload["bcc"] = [self._map_recipient(addr) for addr in message.bcc_emails]

        if message.attachments:
            payload["attachment"] = [
                {
                    "url": "",  # Brevo expects a URL; base64 content not shown here
                    "name": att.filename,
                    "contentType": att.content_type,
                }
                for att in message.attachments
            ]

        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "api-key": self.api_key,
        }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    self.api_url, json=payload, headers=headers
                )
                response.raise_for_status()

            data = response.json()
            message_id = data.get("messageId", "brevo-unknown")

            logger.info(
                "Email sent successfully via Brevo to"
                f" {len(message.to_emails)} recipients"
            )

            return EmailSendResult(
                message_id=str(message_id),
                status="sent",
                provider_response={"provider": "brevo", "message_id": str(message_id)},
            )

        except httpx.HTTPStatusError as e:
            logger.error(f"Brevo API error: {e.response.status_code} {e.response.text}")
            raise EmailSendError(
                f"Brevo API error: {e.response.status_code}",
                provider_error_code=str(e.response.status_code),
            ) from e
        except Exception as e:
            logger.error(f"Failed to send email via Brevo: {e}")
            raise EmailSendError(f"Failed to send email via Brevo: {str(e)}") from e


__all__ = ["BrevoEmailSender"]
