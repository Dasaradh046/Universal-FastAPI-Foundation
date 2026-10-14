"""
Pydantic schemas for the example module.
"""
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class ExampleBase(BaseModel):
    """Base example model."""
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)


class ExampleCreate(ExampleBase):
    """Model for creating an example."""
    pass


class ExampleUpdate(BaseModel):
    """Model for updating an example."""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)


class ExampleInDBBase(ExampleBase):
    """Base model for example stored in DB."""
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True


class Example(ExampleInDBBase):
    """Model for example returned to client."""
    pass


class ExampleInDB(ExampleInDBBase):
    """Model for example stored in DB."""
    pass
