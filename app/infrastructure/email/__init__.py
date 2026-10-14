"""
Email infrastructure package.
"""

from app.infrastructure.email.base import EmailMessage
from app.infrastructure.email.service import EmailService, EmailSendResult, get_email_service

__all__ = ["EmailMessage", "EmailService", "EmailSendResult", "get_email_service"]
