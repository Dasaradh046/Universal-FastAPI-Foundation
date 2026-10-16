"""
Tenant models.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    UUID as SQL_UUID,
    Boolean,
    DateTime,
    Enum,
    String,
    Text,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.security.encryption import EncryptedText
from app.models.base import Base, TenantBase
from app.models.enums import TenantStatus


if TYPE_CHECKING:
    from app.models.user import User


class Tenant(TenantBase, Base):
    """Organization/tenant record."""

    __tablename__ = "tenants"
    __table_args__ = ()

    name: Mapped[str] = mapped_column(String(160), nullable=False)
    slug: Mapped[str] = mapped_column(String(80), unique=True, index=True, nullable=False)
    status: Mapped[TenantStatus] = mapped_column(
        Enum(TenantStatus), default=TenantStatus.ACTIVE, nullable=False
    )
    plan: Mapped[str | None] = mapped_column(String(32), nullable=True)
    is_platform: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False, server_default=text("false")
    )

    # Encrypted sensitive tenant data
    billing_email_encrypted: Mapped[str | None] = mapped_column(EncryptedText, nullable=True)
    billing_address_encrypted: Mapped[str | None] = mapped_column(EncryptedText, nullable=True)
    tax_id_encrypted: Mapped[str | None] = mapped_column(EncryptedText, nullable=True)
    primary_contact_phone_encrypted: Mapped[str | None] = mapped_column(EncryptedText, nullable=True)

    # Settings
    timezone: Mapped[str] = mapped_column(String(64), default="UTC", nullable=False)
    locale: Mapped[str] = mapped_column(String(16), default="en-US", nullable=False)
    password_policy_id: Mapped[uuid.UUID | None] = mapped_column(
        SQL_UUID(as_uuid=True), nullable=True
    )

    users: Mapped[list["User"]] = relationship(
        "User", back_populates="tenant", cascade="all, delete-orphan"
    )


__all__ = ["Tenant"]