"""
Pydantic schemas for the example module.

Follows the application-wide ResponseEnvelope pattern for consistent API responses.
"""

from __future__ import annotations

from typing import Optional, TypeVar, Any
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field, ConfigDict

from app.schemas.common import ResponseEnvelope

T = TypeVar("T")


class ExampleBase(BaseModel):
    """Base example model."""
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)

    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
    )


class ExampleCreate(ExampleBase):
    """Model for creating an example."""
    pass


class ExampleUpdate(BaseModel):
    """Model for updating an example."""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)

    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
    )


class ExampleInDBBase(ExampleBase):
    """Base model for example stored in DB."""
    id: UUID
    tenant_id: UUID
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class ExampleResponse(ExampleInDBBase):
    """Model for example returned to client."""
    pass


class ExampleResponseEnvelope(ResponseEnvelope[ExampleResponse]):
    """Single example response envelope."""
    pass


class ExampleListResponseEnvelope(ResponseEnvelope[list[ExampleResponse]]):
    """List of examples response envelope."""
    pass


__all__ = [
    "ExampleBase",
    "ExampleCreate",
    "ExampleUpdate",
    "ExampleInDBBase",
    "ExampleResponse",
    "ExampleResponseEnvelope",
    "ExampleListResponseEnvelope",
]
