"""
Email service contracts.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Protocol, List, Optional, Dict, Any
from pydantic import BaseModel, Field


class EmailAddress(BaseModel):
    """Email address with optional name."""
    email: str
    name: Optional[str] = None


class EmailAttachment(BaseModel):
    """Email attachment."""
    filename: str
    content: bytes
    content_type: str = "application/octet-stream"


class EmailTemplateData(BaseModel):
    """Template data for email rendering."""
    template_id: str
    data: Dict[str, Any] = Field(default_factory=dict)


class EmailMessage(BaseModel):
    """Email message to be sent."""
    subject: str
    html_content: Optional[str] = None
    text_content: Optional[str] = None
    from_email: EmailAddress
    to_emails: List[EmailAddress] = Field(default_factory=list)
    cc_emails: List[EmailAddress] = Field(default_factory=list)
    bcc_emails: List[EmailAddress] = Field(default_factory=list)
    attachments: List[EmailAttachment] = Field(default_factory=list)
    template_data: Optional[EmailTemplateData] = None
    headers: Dict[str, str] = Field(default_factory=dict)


class EmailSendResult(BaseModel):
    """Result of sending an email."""
    message_id: str
    status: str  # queued, sent, failed, etc.
    provider_response: Optional[Dict[str, Any]] = None


class EmailSender(Protocol):
    """Protocol defining the email sender interface."""
    
    async def send(self, message: EmailMessage) -> EmailSendResult:
        """Send an email message.
        
        Args:
            message: The email message to send
            
        Returns:
            Result of the send operation
            
        Raises:
            EmailSendError: If the email could not be sent
        """
        ...


class EmailSendError(Exception):
    """Exception raised when email sending fails."""
    
    def __init__(self, message: str, provider_error_code: Optional[str] = None):
        super().__init__(message)
        self.provider_error_code = provider_error_code


class EmailBaseService(ABC):
    """Abstract base class for email services."""
    
    @abstractmethod
    async def send_email(self, message: EmailMessage) -> EmailSendResult:
        """Send an email message.
        
        Args:
            message: The email message to send
            
        Returns:
            Result of the send operation
        """
        pass
    
    @abstractmethod
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
        pass
