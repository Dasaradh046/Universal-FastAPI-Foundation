"""
Email service layer.
"""
from typing import List, Optional, Dict, Any

from app.integrations.email.contracts import (
    EmailMessage, 
    EmailSendResult,
    EmailAddress,
    EmailAttachment,
    EmailTemplateData
)
from app.integrations.email.factory import get_email_sender
from app.core.logging import get_logger

logger = get_logger(__name__)


class EmailService:
    """Service for sending emails."""
    
    def __init__(self):
        self.sender = get_email_sender()
    
    async def send_email(
        self,
        subject: str,
        from_email: EmailAddress,
        to_emails: List[EmailAddress],
        *,
        html_content: Optional[str] = None,
        text_content: Optional[str] = None,
        cc_emails: Optional[List[EmailAddress]] = None,
        bcc_emails: Optional[List[EmailAddress]] = None,
        attachments: Optional[List[EmailAttachment]] = None,
        headers: Optional[Dict[str, Any]] = None,
    ) -> EmailSendResult:
        """Send an email.
        
        Args:
            subject: Email subject
            from_email: Sender email address
            to_emails: List of recipient email addresses
            html_content: HTML content of the email
            text_content: Plain text content of the email
            cc_emails: List of CC recipients
            bcc_emails: List of BCC recipients
            attachments: List of attachments
            headers: Additional email headers
            
        Returns:
            Result of the send operation
        """
        message = EmailMessage(
            subject=subject,
            html_content=html_content,
            text_content=text_content,
            from_email=from_email,
            to_emails=to_emails or [],
            cc_emails=cc_emails or [],
            bcc_emails=bcc_emails or [],
            attachments=attachments or [],
            headers=headers or {}
        )
        
        return await self.sender.send(message)
    
    async def send_template_email(
        self,
        template_id: str,
        template_data: Dict[str, Any],
        to_emails: List[EmailAddress],
        from_email: EmailAddress,
        **kwargs
    ) -> EmailSendResult:
        """Send an email using a template.
        
        Args:
            template_id: ID of the template to use
            template_data: Data to render the template with
            to_emails: List of recipients
            from_email: Sender email address
            **kwargs: Additional provider-specific arguments
            
        Returns:
            Result of the send operation
        """
        # In a real implementation, this would render the template
        # For now, we'll just log that we would use a template
        logger.info(f"Would send template email with ID: {template_id}")
        logger.info(f"Template data: {template_data}")
        
        # Fall back to regular email sending with template info in subject
        return await self.send_email(
            subject=f"[Template: {template_id}] {template_data.get('subject', 'No subject')}",
            from_email=from_email,
            to_emails=to_emails,
            html_content=template_data.get("html_content"),
            text_content=template_data.get("text_content"),
        )
    
    async def send_notification_email(
        self,
        to_email: EmailAddress,
        subject: str,
        message: str,
        notification_type: str = "info"
    ) -> EmailSendResult:
        """Send a notification email.
        
        Args:
            to_email: Recipient email address
            subject: Email subject
            message: Email message body
            notification_type: Type of notification (info, warning, error, success)
            
        Returns:
            Result of the send operation
        """
        from_email = EmailAddress(
            email=settings.NOTIFICATIONS_FROM_EMAIL or "noreply@example.com",
            name=settings.NOTIFICATIONS_FROM_NAME or "Universal FastAPI Foundation"
        )
        
        # Add notification type to subject
        full_subject = f"[{notification_type.upper()}] {subject}"
        
        return await self.send_email(
            subject=full_subject,
            from_email=from_email,
            to_emails=[to_email],
            text_content=message
        )
