"""
SMS service factory.
"""

from app.core.config import settings
from app.integrations.sms.contracts import SMSProvider
from app.integrations.sms.providers.log import LogSMSProvider
from app.integrations.sms.providers.twilio import TwilioSMSProvider


def get_sms_provider() -> SMSProvider:
    """Factory function to get the configured SMS provider.

    Returns:
        An instance of the configured SMS provider

    Raises:
        ValueError: If the configured SMS provider is not supported
    """
    provider = settings.SMS_PROVIDER

    if provider == "twilio":
        return TwilioSMSProvider()
    elif provider == "log":
        return LogSMSProvider()
    else:
        raise ValueError(f"Unsupported SMS provider: {provider}")


__all__ = ["get_sms_provider"]
