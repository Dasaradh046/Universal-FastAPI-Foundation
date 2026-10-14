"""
Tests for the email integration.
"""
import pytest
from unittest.mock import AsyncMock, patch

from app.integrations.email.service import EmailService
from app.integrations.email.contracts import EmailAddress


@pytest.mark.asyncio
async def test_send_email():
    """Test sending an email."""
    email_service = EmailService()
    
    # Mock the sender to avoid actually sending emails
    with patch.object(email_service.sender, 'send', return_value=AsyncMock()):
        result = await email_service.send_email(
            subject="Test Email",
            from_email=EmailAddress(email="test@example.com", name="Test Sender"),
            to_emails=[EmailAddress(email="recipient@example.com", name="Recipient")],
            text_content="This is a test email."
        )
        
        assert result is not None
        assert hasattr(result, 'message_id')
        assert hasattr(result, 'status')


@pytest.mark.asyncio
async def test_send_template_email():
    """Test sending a template email."""
    email_service = EmailService()
    
    # Mock the sender to avoid actually sending emails
    with patch.object(email_service.sender, 'send', return_value=AsyncMock()):
        result = await email_service.send_template_email(
            template_id="welcome_template",
            template_data={"username": "testuser", "subject": "Welcome!"},
            to_emails=[EmailAddress(email="newuser@example.com")],
            from_email=EmailAddress(email="welcome@example.com", name="Welcome Team")
        )
        
        assert result is not None
        assert hasattr(result, 'message_id')
        assert hasattr(result, 'status')


@pytest.mark.asyncio
async def test_send_notification_email():
    """Test sending a notification email."""
    email_service = EmailService()
    
    # Mock the sender to avoid actually sending emails
    with patch.object(email_service.sender, 'send', return_value=AsyncMock()):
        result = await email_service.send_notification_email(
            to_email=EmailAddress(email="user@example.com", name="Test User"),
            subject="Test Notification",
            message="This is a test notification.",
            notification_type="info"
        )
        
        assert result is not None
        assert hasattr(result, 'message_id')
        assert hasattr(result, 'status')
