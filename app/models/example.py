"""
Example model for the example module.

This model demonstrates a simple tenant-scoped entity.
"""

from __future__ import annotations

from typing import Optional

from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TenantBase


class Example(TenantBase, Base):
    """Example tenant-scoped entity."""

    __tablename__ = "examples"

    name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)


__all__ = ["Example"]