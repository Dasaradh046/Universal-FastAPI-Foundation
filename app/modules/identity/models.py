"""
SQLAlchemy models for the identity module.

These models are re-exported from app.models for centralized model management.
See app/models/user.py for the full implementation.
"""
from __future__ import annotations

from typing import Optional
from uuid import UUID

from app.models.base import Base, TimestampMixin

from app.models.user import Tenant, User

__all__ = ["Tenant", "User"]
