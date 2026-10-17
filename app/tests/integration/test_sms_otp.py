"""
Tests for the SMS OTP service.
"""

from __future__ import annotations

from app.integrations.sms.otp import (
    SMSOTPStore,
    clear_otp,
    generate_otp,
    sms_otp_store,
    verify_otp,
)


class TestSMSOTPStore:
    """Tests for the SMSOTPStore."""

    def setup_method(self):
        """Clear the store before each test."""
        sms_otp_store._codes.clear()
        sms_otp_store._request_times.clear()

    def test_generate_and_store_otp(self):
        """Generating an OTP stores it and returns the code."""
        store = SMSOTPStore()
        code = store.generate_and_store("+14155552671")

        assert code is not None
        assert len(code) == 6
        assert code.isdigit()

        # Verify the code is stored
        stored = store._codes.get("+14155552671")
        assert stored is not None
        assert stored[0] == code

    def test_generate_otp_custom_length(self):
        """OTP length is configurable via settings."""
        store = SMSOTPStore()
        code = store.generate_and_store("+14155552671")

        assert len(code) == 6  # default SMS_OTP_LENGTH

    def test_verify_valid_otp(self):
        """Verifying a valid OTP returns True."""
        store = SMSOTPStore()
        code = store.generate_and_store("+14155552671")

        assert store.verify("+14155552671", code) is True

    def test_verify_invalid_otp(self):
        """Verifying an invalid OTP returns False."""
        store = SMSOTPStore()
        store.generate_and_store("+14155552671")

        assert store.verify("+14155552671", "000000") is False

    def test_verify_nonexistent_otp(self):
        """Verifying an OTP for a phone with no stored code returns False."""
        store = SMSOTPStore()

        assert store.verify("+14155552671", "123456") is False

    def test_verify_consumes_otp(self):
        """Verifying an OTP consumes it (cannot be reused)."""
        store = SMSOTPStore()
        code = store.generate_and_store("+14155552671")

        assert store.verify("+14155552671", code) is True
        assert store.verify("+14155552671", code) is False

    def test_clear_otp(self):
        """Clearing an OTP removes it from the store."""
        store = SMSOTPStore()
        store.generate_and_store("+14155552671")

        assert "+14155552671" in store._codes

        store.clear("+14155552671")

        assert "+14155552671" not in store._codes

    def test_rate_limiting(self):
        """Rapid OTP requests are rate limited."""
        store = SMSOTPStore()

        # First request should succeed
        assert store.generate_and_store("+14155552671") is not None

        # Immediate second request should be rate limited
        assert store.generate_and_store("+14155552671") is None

    def test_different_numbers_not_rate_limited(self):
        """Different phone numbers are not rate limited against each other."""
        store = SMSOTPStore()

        assert store.generate_and_store("+14155552671") is not None
        assert store.generate_and_store("+14155552672") is not None


class TestModuleLevelOTPFunctions:
    """Tests for the module-level OTP functions."""

    def setup_method(self):
        """Clear the store before each test."""
        sms_otp_store._codes.clear()
        sms_otp_store._request_times.clear()

    def test_generate_otp(self):
        """generate_otp returns a code."""
        code = generate_otp("+14155552671")
        assert code is not None
        assert len(code) == 6

    def test_verify_otp(self):
        """verify_otp works with the module-level store."""
        code = generate_otp("+14155552671")
        assert verify_otp("+14155552671", code) is True
        assert verify_otp("+14155552671", "wrong") is False

    def test_clear_otp(self):
        """clear_otp removes the stored code."""
        generate_otp("+14155552671")
        clear_otp("+14155552671")
        assert verify_otp("+14155552671", "123456") is False
