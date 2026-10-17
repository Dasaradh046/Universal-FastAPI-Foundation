"""
Events for the example module.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass
class ExampleCreated:
    """Event raised when an example is created."""

    example_id: UUID
    tenant_id: UUID
    name: str
    created_at: datetime


@dataclass
class ExampleUpdated:
    """Event raised when an example is updated."""

    example_id: UUID
    tenant_id: UUID
    name: str
    updated_at: datetime


@dataclass
class ExampleDeleted:
    """Event raised when an example is deleted."""

    example_id: UUID
    tenant_id: UUID
    deleted_at: datetime


__all__ = [
    "ExampleCreated",
    "ExampleUpdated",
    "ExampleDeleted",
]
