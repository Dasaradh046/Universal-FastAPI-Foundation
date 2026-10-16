"""
Pydantic schemas for the audit module.

Follows the application-wide ResponseEnvelope pattern for consistent API responses.
"""

from __future__ import annotations

from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, Generic, TypeVar, Any
from datetime import datetime
from uuid import UUID

from app.schemas.common import ResponseEnvelope
from app.models.enums import AuditAction

T = TypeVar("T")


class AuditLogBase(BaseModel):
    """Base audit log model."""
    action: AuditAction = Field(..., description="Type of audit action")
    resource: str = Field(..., max_length=100, description="Resource type (e.g., 'user', 'tenant')")
    resource_id: Optional[str] = Field(None, max_length=255, description="ID of the affected resource")
    description: Optional[str] = Field(None, max_length=1000, description="Human-readable description")
    before_state: Optional[dict[str, Any]] = Field(None, description="State before the action")
    after_state: Optional[dict[str, Any]] = Field(None, description="State after the action")
    ip_address: Optional[str] = Field(None, max_length=64, description="Client IP address")
    user_agent: Optional[str] = Field(None, max_length=500, description="Client user agent")

    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
    )


class AuditLogCreate(AuditLogBase):
    """Model for creating an audit log entry."""
    tenant_id: UUID = Field(..., description="Tenant ID")
    actor_user_id: Optional[UUID] = Field(None, description="User ID who performed the action")

    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
    )


class AuditLogInDBBase(AuditLogBase):
    """Base model for audit log stored in DB."""
    id: UUID
    tenant_id: UUID
    actor_user_id: Optional[UUID] = None
    created_at: datetime

    model_config = ConfigDict(
        from_attributes=True,
    )


class AuditLogResponse(AuditLogInDBBase):
    """Model for audit log returned to client."""
    pass


class AuditLogInDB(AuditLogInDBBase):
    """Model for audit log stored in DB."""
    pass


# Query/filter schemas
class AuditLogFilter(BaseModel):
    """Filter parameters for audit log queries."""
    action: Optional[AuditAction] = None
    resource: Optional[str] = None
    resource_id: Optional[str] = None
    actor_user_id: Optional[UUID] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    ip_address: Optional[str] = None

    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
    )


# Response envelope specializations
class AuditLogResponseEnvelope(ResponseEnvelope[AuditLogResponse]):
    """Single audit log response envelope."""
    pass


class AuditLogListResponseEnvelope(ResponseEnvelope[list[AuditLogResponse]]):
    """List of audit logs response envelope."""
    pass


__all__ = [
    "AuditLogBase",
    "AuditLogCreate",
    "AuditLogInDBBase",
    "AuditLogResponse",
    "AuditLogInDB",
    "AuditLogFilter",
    "AuditLogResponseEnvelope",
    "AuditLogListResponseEnvelope",
]