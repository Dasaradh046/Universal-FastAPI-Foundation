"""
Email API endpoints.
"""
from fastapi import APIRouter, BackgroundTasks, HTTPException, status
from pydantic import BaseModel, EmailStr
from typing import List, Optional, Dict, Any

from app.integrations.email.service import EmailService
from app.integrations.email.contracts import EmailAddress

router = APIRouter(prefix="/email", tags=["email"])


class EmailRequest(BaseModel):
    """Request model for sending an email."""
    subject: str
    to_email: EmailStr
    html_content: Optional[str] = None
    text_content: Optional[str] = None
    template_id: Optional[str] = None
    template_data: Optional[Dict[str, Any]] = None


class EmailResponse(BaseModel):
    """Response model for email sending."""
    message_id: str
    status: str
    detail: str


@router.post("/send", response_model=EmailResponse, status_code=status.HTTP_202_ACCEPTED)
async def send_email(
    email_request: EmailRequest,
    background_tasks: BackgroundTasks,
):
    """Send an email."""
    email_service = EmailService()
    
    # Convert to internal EmailAddress format
    to_email_addr = EmailAddress(email=email_request.to_email)
    from_email_addr = EmailAddress(
        email=settings.NOTIFICATIONS_FROM_EMAIL or "noreply@example.com",
        name=settings.NOTIFICATIONS_FROM_NAME or "Universal FastAPI Foundation"
    )
    
    try:
        if email_request.template_id and email_request.template_data:
            # Send template email
            result = await email_service.send_template_email(
                template_id=email_request.template_id,
                template_data=email_request.template_data or {},
                to_emails=[to_email_addr],
                from_email=from_email_addr
            )
        else:
            # Send regular email
            result = await email_service.send_email(
                subject=email_request.subject,
                from_email=from_email_addr,
                to_emails=[to_email_addr],
                html_content=email_request.html_content,
                text_content=email_request.text_content
            )
        
        return EmailResponse(
            message_id=result.message_id,
            status=result.status,
            detail="Email queued for sending"
        )
    except Exception as e:
        logger.error(f"Failed to send email: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to send email: {str(e)}"
        )


@router.post("/notification", response_model=EmailResponse, status_code=status.HTTP_202_ACCEPTED)
async def send_notification_email(
    to_email: EmailStr,
    subject: str,
    message: str,
    notification_type: str = "info",
    background_tasks: BackgroundTasks = None,
):
    """Send a notification email."""
    email_service = EmailService()
    
    # Convert to internal EmailAddress format
    to_email_addr = EmailAddress(email=to_email)
    
    try:
        result = await email_service.send_notification_email(
            to_email=to_email_addr,
            subject=subject,
            message=message,
            notification_type=notification_type
        )
        
        return EmailResponse(
            message_id=result.message_id,
            status=result.status,
            detail="Notification email queued for sending"
        )
    except Exception as e:
        logger.error(f"Failed to send notification email: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to send notification email: {str(e)}"
        )
