"""
Pydantic schemas for the example module.
"""
from __future__ import annotations

from pydantic import BaseModel, Field, ConfigDict
from typing import Optional
from datetime import datetime
from uuid import UUID


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
    updated_at: datetime
    
    model_config = ConfigDict(
        from_attributes=True,
    )


class ExampleResponse(ExampleInDBBase):
    """Model for example returned to client."""
    pass


class ExampleInDB(ExampleInDBBase):
    """Model for example stored in DB."""
    pass


__all__ = [
    "ExampleBase",
    "ExampleCreate",
    "ExampleUpdate",
    "ExampleInDBBase",
    "ExampleResponse",
    "ExampleInDB",
]