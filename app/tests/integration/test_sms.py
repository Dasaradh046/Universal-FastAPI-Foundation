"""
Tests for the SMS provider adapters.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from httpx import Response

from app.integrations.sms.contracts import (
    PhoneNumber,
    SMSMessage,
)
from app.integrations.sms.providers.log import LogSMSProvider
from app.integrations.sms.providers.twilio import TwilioSMSProvider


@pytest.fixture
def twilio_provider():
    """Create a TwilioSMSProvider with test credentials."""
    with patch("app.integrations.sms.providers.twilio.settings") as mock_settings:
        mock_settings.TWILIO_ACCOUNT_SID = "ACtestaccountsid123"
        mock_settings.TWILIO_AUTH_TOKEN = "testauthtoken456"
        mock_settings.TWILIO_FROM_NUMBER = "+14155552671"
        return TwilioSMSProvider()


@pytest.fixture
def log_provider():
    """Create a LogSMSProvider."""
    return LogSMSProvider()


@pytest.fixture
def sms_message():
    """Create a test SMS message."""
    return SMSMessage(
        to=PhoneNumber(number="+14155552671"),
        from_number="+14155551234",
        body="Your verification code is 123456",
    )


class TestTwilioSMSProvider:
    """Tests for the TwilioSMSProvider."""

    def test_provider_initialization(self, twilio_provider):
        """TwilioSMSProvider initializes with credentials."""
        assert twilio_provider.account_sid == "ACtestaccountsid123"
        assert twilio_provider.auth_token == "testauthtoken456"
        assert twilio_provider.from_number == "+14155552671"
        assert "twilio.com" in twilio_provider.api_url

    def test_provider_requires_credentials(self):
        """TwilioSMSProvider raises ValueError when credentials are missing."""
        with patch("app.integrations.sms.providers.twilio.settings") as mock_settings:
            mock_settings.TWILIO_ACCOUNT_SID = None
            mock_settings.TWILIO_AUTH_TOKEN = "token"
            mock_settings.TWILIO_FROM_NUMBER = "+14155551234"
            with pytest.raises(ValueError, match="TWILIO_ACCOUNT_SID"):
                TwilioSMSProvider()

    @pytest.mark.asyncio
    async def test_send_success(self, twilio_provider, sms_message):
        """Sending an SMS via Twilio returns a successful result."""
        mock_response = AsyncMock(spec=Response)
        mock_response.status_code = 201
        mock_response.raise_for_status = AsyncMock()
        mock_response.json.return_value = {
            "sid": "SMtestmessageid123",
            "status": "queued",
        }

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client.post = AsyncMock(return_value=mock_response)

        with patch(
            "app.integrations.sms.providers.twilio.httpx.AsyncClient",
            return_value=mock_client,
        ):
            result = await twilio_provider.send(sms_message)

        assert result.message_id == "SMtestmessageid123"
        assert result.status == "sent"
        assert result.provider_response["provider"] == "twilio"

    @pytest.mark.asyncio
    async def test_send_api_error(self, twilio_provider, sms_message):
        """Sending an SMS via Twilio raises SMSSendError on API error."""
        mock_response = AsyncMock(spec=Response)
        mock_response.status_code = 401
        mock_response.text = "Unauthorized"

        def raise_for_status():
            raise Exception("401 Unauthorized")

        mock_response.raise_for_status = raise_for_status

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client.post = AsyncMock(return_value=mock_response)

        with patch(
            "app.integrations.sms.providers.twilio.httpx.AsyncClient",
            return_value=mock_client,
        ):
            from app.integrations.sms.contracts import SMSSendError

            with pytest.raises(SMSSendError):
                await twilio_provider.send(sms_message)


class TestLogSMSProvider:
    """Tests for the LogSMSProvider."""

    @pytest.mark.asyncio
    async def test_send_logs_message(self, log_provider, sms_message):
        """LogSMSProvider logs the message instead of sending it."""
        result = await log_provider.send(sms_message)

        assert result.status == "sent"
        assert result.provider_response["logged"] is True
        assert result.message_id.startswith("log-")


class TestPhoneNumber:
    """Tests for the PhoneNumber contract."""

    def test_valid_e164_number(self):
        """Valid E.164 phone numbers are accepted."""
        phone = PhoneNumber(number="+14155552671")
        assert phone.number == "+14155552671"

    def test_invalid_number_raises(self):
        """Invalid phone numbers raise ValueError."""
        with pytest.raises(ValueError):
            PhoneNumber(number="not-a-phone-number")

    def test_short_number_raises(self):
        """Too-short phone numbers raise ValueError."""
        with pytest.raises(ValueError):
            PhoneNumber(number="+1")
