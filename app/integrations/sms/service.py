"""
SMS service layer.
"""

from typing import Optional

from app.core.config import settings
from app.core.logging import get_logger
from app.integrations.sms.contracts import (
    PhoneNumber,
    SMSMessage,
    SMSSendResult,
)
from app.integrations.sms.factory import get_sms_provider

logger = get_logger(__name__)


class SMSService:
    """Service for sending SMS messages."""

    def __init__(self):
        self.provider = get_sms_provider()

    async def send_sms(
        self,
        to: str,
        body: str,
        from_number: Optional[str] = None,
    ) -> SMSSendResult:
        """Send an SMS message.

        Args:
            to: Recipient phone number (E.164 format)
            body: SMS message body
            from_number: Optional sender phone number

        Returns:
            Result of the send operation
        """
        phone_number = PhoneNumber(number=to)

        message = SMSMessage(
            to=phone_number,
            from_number=from_number or settings.TWILIO_FROM_NUMBER,
            body=body,
        )

        return await self.provider.send(message)

    async def send_notification_sms(
        self,
        to: str,
        message: str,
        notification_type: str = "info",
    ) -> SMSSendResult:
        """Send a notification SMS.

        Args:
            to: Recipient phone number (E.164 format)
            message: SMS message body
            notification_type: Type of notification (info, warning, error, success)

        Returns:
            Result of the send operation
        """
        full_message = f"[{notification_type.upper()}] {message}"
        return await self.send_sms(to=to, body=full_message)
