"""
Response schemas — application-wide response formats.
"""

from __future__ import annotations

from typing import Any, Generic, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class ResponseEnvelope(BaseModel, Generic[T]):
    """Application-wide response envelope."""

    success: bool
    status_code: int
    message: str
    data: T | None = None
    meta: dict[str, Any] | None = None


class ErrorResponse(BaseModel):
    """Standard error response."""

    success: bool = False
    status_code: int
    message: str
    data: None = None
    meta: dict[str, Any] | None = None


__all__ = ["ResponseEnvelope", "ErrorResponse"]
