"""
Email service factory.
"""
from typing import Literal

from app.integrations.email.contracts import EmailSender
from app.integrations.email.providers.smtp import SMTPEmailSender
from app.core.config import settings


def get_email_sender() -> EmailSender:
    """Factory function to get the configured email sender.
    
    Returns:
        An instance of the configured email sender
        
    Raises:
        ValueError: If the configured email provider is not supported
    """
    provider = settings.EMAIL_PROVIDER
    
    if provider == "smtp":
        return SMTPEmailSender()
    elif provider == "log":
        # For development, we can just log emails instead of sending them
        from app.integrations.email.providers.log import LogEmailSender
        return LogEmailSender()
    else:
        raise ValueError(f"Unsupported email provider: {provider}")
