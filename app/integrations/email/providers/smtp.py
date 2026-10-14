"""
SMTP email provider implementation.
"""
import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from typing import List

from app.integrations.email.contracts import (
    EmailSender, 
    EmailMessage, 
    EmailSendResult,
    EmailAddress,
    EmailAttachment,
    EmailSendError
)
from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class SMTPEmailSender(EmailSender):
    """SMTP email sender implementation."""
    
    def __init__(self):
        self.host = settings.SMTP_HOST
        self.port = settings.SMTP_PORT
        self.username = settings.SMTP_USER
        self.password = settings.SMTP_PASSWORD
        self.use_tls = settings.SMTP_TLS
        self.use_ssl = settings.SMTP_SSL
        
        if not self.host:
            raise ValueError("SMTP_HOST must be configured")
    
    async def send(self, message: EmailMessage) -> EmailSendResult:
        """Send an email via SMTP.
        
        Args:
            message: The email message to send
            
        Returns:
            Result of the send operation
        """
        try:
            # Create message container
            msg = MIMEMultipart()
            msg["From"] = f"{message.from_email.name} <{message.from_email.email}>" if message.from_email.name else message.from_email.email
            msg["To"] = ", ".join([f"{addr.name} <{addr.email}>" if addr.name else addr.email for addr in message.to_emails])
            msg["Subject"] = message.subject
            
            # Add CC and BCC if present
            if message.cc_emails:
                msg["Cc"] = ", ".join([f"{addr.name} <{addr.email}>" if addr.name else addr.email for addr in message.cc_emails])
            if message.bcc_emails:
                msg["Bcc"] = ", ".join([f"{addr.name} <{addr.email}>" if addr.name else addr.email for addr in message.bcc_emails])
            
            # Add custom headers
            for key, value in message.headers.items():
                msg[key] = value
            
            # Add body content
            if message.text_content:
                msg.attach(MIMEText(message.text_content, "plain"))
            if message.html_content:
                msg.attach(MIMEText(message.html_content, "html"))
            
            # Add attachments
            for attachment in message.attachments:
                part = MIMEBase("application", "octet-stream")
                part.set_payload(attachment.content)
                encoders.encode_base64(part)
                part.add_header(
                    "Content-Disposition",
                    f"attachment; filename= {attachment.filename}",
                )
                msg.attach(part)
            
            # Convert to string
            text = msg.as_string()
            
            # Connect to server and send email
            context = ssl.create_default_context()
            
            if self.use_ssl:
                # SSL connection
                with smtplib.SMTP_SSL(self.host, self.port, context=context) as server:
                    if self.username and self.password:
                        server.login(self.username, self.password)
                    recipients = [addr.email for addr in message.to_emails]
                    recipients.extend([addr.email for addr in message.cc_emails])
                    recipients.extend([addr.email for addr in message.bcc_emails])
                    server.sendmail(message.from_email.email, recipients, text)
            else:
                # Regular connection with optional TLS
                with smtplib.SMTP(self.host, self.port) as server:
                    if self.use_tls:
                        server.starttls(context=context)
                    if self.username and self.password:
                        server.login(self.username, self.password)
                    recipients = [addr.email for addr in message.to_emails]
                    recipients.extend([addr.email for addr in message.cc_emails])
                    recipients.extend([addr.email for addr in message.bcc_emails])
                    server.sendmail(message.from_email.email, recipients, text)
            
            logger.info(f"Email sent successfully to {len(message.to_emails)} recipients")
            
            return EmailSendResult(
                message_id=f"smtp-{hash(text)}",
                status="sent",
                provider_response={"smtp_response": "Email sent successfully"}
            )
            
        except Exception as e:
            logger.error(f"Failed to send email via SMTP: {e}")
            raise EmailSendError(f"Failed to send email: {str(e)}") from e
