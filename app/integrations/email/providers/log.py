"""
Logging email provider for development.
"""
from app.integrations.email.contracts import (
    EmailSender, 
    EmailMessage, 
    EmailSendResult,
    EmailSendError
)
from app.core.logging import get_logger

logger = get_logger(__name__)


class LogEmailSender(EmailSender):
    """Email sender that logs messages instead of sending them (for development)."""
    
    async def send(self, message: EmailMessage) -> EmailSendResult:
        """Log an email message instead of sending it.
        
        Args:
            message: The email message to log
            
        Returns:
            Result indicating the email was "sent"
        """
        logger.info(f"Email would be sent: {message.subject}")
        logger.info(f"From: {message.from_email.email}")
        logger.info(f"To: {[addr.email for addr in message.to_emails]}")
        if message.cc_emails:
            logger.info(f"CC: {[addr.email for addr in message.cc_emails]}")
        if message.bcc_emails:
            logger.info(f"BCC: {[addr.email for addr in message.bcc_emails]}")
        logger.info(f"Headers: {message.headers}")
        
        if message.text_content:
            logger.info(f"Text content: {message.text_content[:200]}...")
        if message.html_content:
            logger.info(f"HTML content: {message.html_content[:200]}...")
        
        if message.attachments:
            logger.info(f"Attachments: {[att.filename for att in message.attachments]}")
        
        return EmailSendResult(
            message_id=f"log-{hash(message.subject)}",
            status="sent",
            provider_response={"logged": True}
        )
