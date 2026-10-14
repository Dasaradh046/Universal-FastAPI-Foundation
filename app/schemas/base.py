"""
Base response schema using ORM Mode.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class ORMBase(BaseModel):
    """Base model that auto-populates from ORM objects.

    Legacy support — new endpoints should use the ResponseEnvelope instead.
    """

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class PaginationMeta(BaseModel):
    """Pagination metadata."""

    page: int
    page_size: int
    total: int
    total_pages: int


class PaginatedResponse(ORMBase):
    """Generic paginated response wrapper (legacy)."""

    items: list
    total: int
    page: int
    page_size: int
    total_pages: int = 0


__all__ = ["ORMBase", "PaginationMeta", "PaginatedResponse"]
