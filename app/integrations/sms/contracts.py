"""
SMS service contracts.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, Protocol

from pydantic import BaseModel, field_validator


class PhoneNumber(BaseModel):
    """Phone number with E.164 format validation."""

    number: str
    country_code: Optional[str] = None

    @field_validator("number")
    @classmethod
    def _validate_e164(cls, v: str) -> str:
        """Validate E.164 phone number format."""
        import re

        if not re.match(r"^\+?[1-9]\d{1,14}$", v):
            raise ValueError("Phone number must be in E.164 format (e.g. +14155552671)")
        return v


class SMSMessage(BaseModel):
    """SMS message to be sent."""

    to: PhoneNumber
    from_number: Optional[str] = None
    body: str


class SMSSendResult(BaseModel):
    """Result of sending an SMS."""

    message_id: str
    status: str  # queued, sent, failed, etc.
    provider_response: Optional[Dict[str, Any]] = None


class SMSProvider(Protocol):
    """Protocol defining the SMS provider interface."""

    async def send(self, message: SMSMessage) -> SMSSendResult:
        """Send an SMS message.

        Args:
            message: The SMS message to send

        Returns:
            Result of the send operation

        Raises:
            SMSSendError: If the SMS could not be sent
        """
        ...


class SMSSendError(Exception):
    """Exception raised when SMS sending fails."""

    def __init__(self, message: str, provider_error_code: Optional[str] = None):
        super().__init__(message)
        self.provider_error_code = provider_error_code


class SMSBaseService(ABC):
    """Abstract base class for SMS services."""

    @abstractmethod
    async def send_sms(self, message: SMSMessage) -> SMSSendResult:
        """Send an SMS message.

        Args:
            message: The SMS message to send

        Returns:
            Result of the send operation
        """
        pass
