"""
Audit log model for security and compliance tracking.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional, TYPE_CHECKING

from sqlalchemy import (
    UUID as SQL_UUID,
    String,
    Text,
    DateTime,
    Enum,
    ForeignKey,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, UUIDPrimaryKey, TenantBase, TimestampMixin
from app.models.enums import AuditAction

if TYPE_CHECKING:
    from app.models.user import User  # noqa: F401
class AuditLog(TenantBase, TimestampMixin, Base):
    """Audit log entry for security and compliance tracking.

    Each entry records a security-relevant event with full context
    for compliance, forensics, and debugging.
    """

    __tablename__ = "audit_logs"

    action: Mapped[AuditAction] = mapped_column(
        Enum(AuditAction),
        nullable=False,
        index=True,
    )
    resource: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    resource_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)

    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # State snapshots for change tracking (stored as JSON)
    before_state: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    after_state: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Request context
    ip_address: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    user_agent: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Actor information
    actor_user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        SQL_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # Relationship to actor user (optional)
    actor: Mapped[Optional["User"]] = relationship(
        "User",
        backref="audit_logs",
        foreign_keys=[actor_user_id],
        lazy="selectin",
    )


__all__ = ["AuditLog"]