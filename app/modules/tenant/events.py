"""
Domain events for the tenant module.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from uuid import UUID


@dataclass
class TenantContextResolved:
    """Event raised when tenant context is resolved."""

    tenant_id: UUID
    resolved_at: datetime


@dataclass
class TenantSwitched:
    """Event raised when tenant context is switched."""

    tenant_id: UUID
    switched_by: Optional[UUID] = None
    switched_at: Optional[datetime] = None


__all__ = [
    "TenantContextResolved",
    "TenantSwitched",
]
