"""
Common schemas: response envelope, error detail, pagination.

Every endpoint can return the same JSON envelope:

    {
        "success": true,
        "status_code": 200,
        "message": "Operation completed successfully",
        "data": {...},
        "meta": {...}
    }

Errors use the same envelope with ``success: false``.
"""

from __future__ import annotations

from typing import Any, Generic, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class PaginationMeta(BaseModel):
    """Pagination metadata."""

    page: int
    page_size: int
    total: int
    total_pages: int


class ErrorDetail(BaseModel):
    """A single validation error detail."""

    field: str
    message: str


class ResponseEnvelope(BaseModel, Generic[T]):
    """Application-wide response envelope."""

    success: bool
    status_code: int
    message: str
    data: T | None = None
    meta: dict[str, Any] | None = None


def ok(data: T | None = None, message: str = "Operation completed successfully",
       meta: dict[str, Any] | None = None) -> ResponseEnvelope:
    """Build a success response envelope."""
    return ResponseEnvelope(success=True, status_code=200, message=message, data=data, meta=meta)


def created(data: T | None = None, message: str = "Resource created successfully",
            meta: dict[str, Any] | None = None) -> ResponseEnvelope:
    """Build a 201 created response envelope."""
    return ResponseEnvelope(success=True, status_code=201, message=message, data=data, meta=meta)


def paginated(
    items: list,
    total: int,
    page: int,
    page_size: int,
    message: str = "Data retrieved successfully",
) -> ResponseEnvelope:
    """Build a paginated response envelope."""
    import math

    total_pages = math.ceil(total / page_size) if page_size > 0 else 0
    meta = PaginationMeta(
        page=page, page_size=page_size, total=total, total_pages=total_pages
    ).model_dump()
    return ResponseEnvelope(
        success=True, status_code=200, message=message, data=items, meta=meta
    )


__all__ = [
    "PaginationMeta",
    "ErrorDetail",
    "ResponseEnvelope",
    "ok",
    "created",
    "paginated",
]