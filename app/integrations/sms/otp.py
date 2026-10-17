"""
SMS OTP (one-time passcode) service.

Generates, stores, and verifies SMS-based OTP codes for phone verification.
"""

from __future__ import annotations

import secrets
import time
from typing import Dict, Optional, Tuple

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class SMSOTPStore:
    """In-memory store for SMS OTP codes with rate limiting.

    In production, this should be backed by Redis for distributed deployments.
    """

    def __init__(self):
        self._codes: Dict[str, Tuple[str, float]] = {}
        self._request_times: Dict[str, float] = {}

    def _now(self) -> float:
        return time.time()

    def _is_rate_limited(self, phone_number: str) -> bool:
        """Check if the phone number is rate limited for OTP requests."""
        last_request = self._request_times.get(phone_number)
        if last_request is None:
            return False
        elapsed = self._now() - last_request
        return elapsed < settings.SMS_OTP_RATE_LIMIT_WINDOW

    def generate_and_store(self, phone_number: str) -> Optional[str]:
        """Generate a new OTP code and store it for the given phone number.

        Returns:
            The generated OTP code (for testing), or None if rate limited.
        """
        if self._is_rate_limited(phone_number):
            logger.warning(f"OTP request rate limited for {phone_number}")
            return None

        code = "".join(
            secrets.choice("0123456789") for _ in range(settings.SMS_OTP_LENGTH)
        )
        expires_at = self._now() + (settings.SMS_OTP_EXPIRE_MINUTES * 60)

        self._codes[phone_number] = (code, expires_at)
        self._request_times[phone_number] = self._now()

        logger.info(f"OTP generated for {phone_number}")
        return code

    def verify(self, phone_number: str, code: str) -> bool:
        """Verify an OTP code for the given phone number.

        Args:
            phone_number: The phone number (E.164 format)
            code: The OTP code to verify

        Returns:
            True if the code is valid and not expired, False otherwise.
        """
        stored = self._codes.get(phone_number)
        if stored is None:
            logger.warning(f"No OTP found for {phone_number}")
            return False

        stored_code, expires_at = stored
        now = self._now()

        if now > expires_at:
            logger.warning(f"OTP expired for {phone_number}")
            del self._codes[phone_number]
            return False

        if not secrets.compare_digest(stored_code, code):
            logger.warning(f"Invalid OTP for {phone_number}")
            return False

        # Consume the code after successful verification
        del self._codes[phone_number]
        logger.info(f"OTP verified for {phone_number}")
        return True

    def clear(self, phone_number: str) -> None:
        """Clear any stored OTP for the given phone number."""
        self._codes.pop(phone_number, None)
        self._request_times.pop(phone_number, None)


# Module-level singleton
sms_otp_store = SMSOTPStore()


def generate_otp(phone_number: str) -> Optional[str]:
    """Generate and store an OTP code for the given phone number.

    Args:
        phone_number: The phone number (E.164 format)

    Returns:
        The generated OTP code, or None if rate limited.
    """
    return sms_otp_store.generate_and_store(phone_number)


def verify_otp(phone_number: str, code: str) -> bool:
    """Verify an OTP code for the given phone number.

    Args:
        phone_number: The phone number (E.164 format)
        code: The OTP code to verify

    Returns:
        True if the code is valid and not expired, False otherwise.
    """
    return sms_otp_store.verify(phone_number, code)


def clear_otp(phone_number: str) -> None:
    """Clear any stored OTP for the given phone number."""
    sms_otp_store.clear(phone_number)


__all__ = [
    "SMSOTPStore",
    "sms_otp_store",
    "generate_otp",
    "verify_otp",
    "clear_otp",
]
