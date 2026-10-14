"""
Shared SQLAlchemy base, mixins, and naming conventions.

All ORM models should import Base from this module so that Alembic can
discover metadata consistently across the application and its modules.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import (
    UUID as SQL_UUID,
    Boolean,
    DateTime,
    Index,
    ForeignKey,
    MetaData,
    String,
    text,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

# Naming convention for automatic index/constraint naming
NAMING_CONVENTION: dict[str, str] = {
    "ix": "ix_%(table_name)s_%(column_0_name)s",
    "ufk": "ufk_%(table_name)s_%(column_0_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "cv": "cv_%(table_name)s_%(column_0_name)s",
}

_metadata = MetaData(naming_convention=NAMING_CONVENTION)


class Base(DeclarativeBase):
    """Declarative base for all ORM models.

    Tables that need tenant awareness should inherit the ``TenantBase`` mixin
    or add a ``tenant_id`` column explicitly.
    """

    metadata = _metadata


class UUIDPrimaryKey:
    """Mixin providing a UUID primary key named ``id``."""

    id: Mapped[uuid.UUID] = mapped_column(
        SQL_UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )


class TimestampMixin:
    """Mixin providing ``created_at`` and ``updated_at`` columns."""

    created_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        server_default=text("now()"),
        index=True,
    )
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        server_default=text("now()"),
        onupdate=lambda: __import__("datetime").datetime.now(tz=__import__("datetime").timezone.utc),
    )


class TenantBase(UUIDPrimaryKey, TimestampMixin):
    """Base for tenant-scoped models.

    Adds a non-null ``tenant_id`` foreign key. Tenant-scoped indexes are
    recommended on every tenant-owned table for query performance.
    """

    __abstract__ = True

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        SQL_UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )


__all__ = [
    "Base",
    "UUIDPrimaryKey",
    "TimestampMixin",
    "TenantBase",
    "NAMING_CONVENTION",
]
