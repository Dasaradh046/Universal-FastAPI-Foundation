"""
Logging SMS provider for development.
"""

from __future__ import annotations

from app.core.logging import get_logger
from app.integrations.sms.contracts import (
    SMSMessage,
    SMSProvider,
    SMSSendResult,
)

logger = get_logger(__name__)


class LogSMSProvider(SMSProvider):
    """SMS provider that logs messages instead of sending them (for development)."""

    async def send(self, message: SMSMessage) -> SMSSendResult:
        """Log an SMS message instead of sending it.

        Args:
            message: The SMS message to log

        Returns:
            Result indicating the SMS was "sent"
        """
        logger.info(f"SMS would be sent to: {message.to.number}")
        logger.info(f"From: {message.from_number}")
        logger.info(f"Body: {message.body}")

        return SMSSendResult(
            message_id=f"log-{hash(message.body)}",
            status="sent",
            provider_response={"logged": True},
        )


__all__ = ["LogSMSProvider"]
