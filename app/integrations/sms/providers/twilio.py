"""
Twilio SMS provider adapter.

Implements the ``SMSProvider`` protocol using Twilio's REST API.

Twilio API reference: https://www.twilio.com/docs/sms/api
"""

from __future__ import annotations

import httpx

from app.core.config import settings
from app.core.logging import get_logger
from app.integrations.sms.contracts import (
    SMSMessage,
    SMSProvider,
    SMSSendError,
    SMSSendResult,
)

logger = get_logger(__name__)

TWILIO_API_URL = (
    "https://api.twilio.com/2010-04-01/Accounts/{account_sid}/Messages.json"
)


class TwilioSMSProvider(SMSProvider):
    """Twilio SMS provider implementation."""

    def __init__(self):
        self.account_sid = settings.TWILIO_ACCOUNT_SID
        self.auth_token = settings.TWILIO_AUTH_TOKEN
        self.from_number = settings.TWILIO_FROM_NUMBER

        if not self.account_sid:
            raise ValueError(
                "TWILIO_ACCOUNT_SID must be configured for the Twilio provider"
            )
        if not self.auth_token:
            raise ValueError(
                "TWILIO_AUTH_TOKEN must be configured for the Twilio provider"
            )
        if not self.from_number:
            raise ValueError(
                "TWILIO_FROM_NUMBER must be configured for the Twilio provider"
            )

        self.api_url = TWILIO_API_URL.format(account_sid=self.account_sid)

    async def send(self, message: SMSMessage) -> SMSSendResult:
        """Send an SMS via Twilio's REST API.

        Args:
            message: The SMS message to send

        Returns:
            Result of the send operation

        Raises:
            SMSSendError: If the SMS could not be sent
        """
        payload = {
            "To": message.to.number,
            "From": message.from_number or self.from_number,
            "Body": message.body,
        }

        headers = {
            "Accept": "application/json",
            "Content-Type": "application/x-www-form-urlencoded",
        }

        auth = httpx.BasicAuth(username=self.account_sid, password=self.auth_token)

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    self.api_url, data=payload, headers=headers, auth=auth
                )
                response.raise_for_status()

            data = response.json()
            message_id = data.get("sid", "twilio-unknown")

            logger.info(f"SMS sent successfully via Twilio to {message.to.number}")

            return SMSSendResult(
                message_id=str(message_id),
                status="sent",
                provider_response={
                    "provider": "twilio",
                    "message_id": str(message_id),
                    "status": data.get("status"),
                },
            )

        except httpx.HTTPStatusError as e:
            logger.error(
                f"Twilio API error: {e.response.status_code} {e.response.text}"
            )
            raise SMSSendError(
                f"Twilio API error: {e.response.status_code}",
                provider_error_code=str(e.response.status_code),
            ) from e
        except Exception as e:
            logger.error(f"Failed to send SMS via Twilio: {e}")
            raise SMSSendError(f"Failed to send SMS via Twilio: {str(e)}") from e


__all__ = ["TwilioSMSProvider"]
