"""
User and session models for the auth and identity modules.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta
from typing import TYPE_CHECKING

from sqlalchemy import (
    UUID as SQL_UUID,
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.encryption import EncryptedText
from app.models.base import Base, UUIDPrimaryKey, TenantBase
from app.core.enums import Role

if TYPE_CHECKING:
    from app.models.tenant import Tenant

# Role alias normalization
from app.core.role_aliases import ROLE_ALIASES


class Tenant(TenantBase, Base):
    """Organization/tenant record."""

    __tablename__ = "tenants"
    __table_args__ = ()

    name: Mapped[str] = mapped_column(String(160), nullable=False)
    slug: Mapped[str] = mapped_column(String(80), unique=True, index=True, nullable=False)
    status: Mapped[str] = mapped_column(
        Enum("ACTIVE", "TRIAL", "SUSPENDED", "ARCHIVED", name="tenant_status"),
        default="ACTIVE",
        nullable=False,
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


class User(Base):
    """A login-capable account within a tenant."""

    __tablename__ = "users"
    __table_args__ = (
        # Unique constraint on email per tenant
        # This is handled by the application layer for tenant isolation
    )

    id: Mapped[uuid.UUID] = mapped_column(
        SQL_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        SQL_UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )

    # ---- Identity -------------------------------------------------------- #
    email: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    email_verified: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False, server_default=text("false")
    )
    email_verified_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    name: Mapped[str | None] = mapped_column(String(160), nullable=True)
    first_name: Mapped[str | None] = mapped_column(String(80), nullable=True)
    last_name: Mapped[str | None] = mapped_column(String(80), nullable=True)
    job_title: Mapped[str | None] = mapped_column(String(120), nullable=True)
    avatar_color: Mapped[str | None] = mapped_column(String(16), nullable=True)
    initials: Mapped[str | None] = mapped_column(String(8), nullable=True)

    # Encrypted PII fields
    phone_encrypted: Mapped[str | None] = mapped_column(EncryptedText, nullable=True)
    address_encrypted: Mapped[str | None] = mapped_column(EncryptedText, nullable=True)
    date_of_birth_encrypted: Mapped[str | None] = mapped_column(EncryptedText, nullable=True)
    government_id_encrypted: Mapped[str | None] = mapped_column(EncryptedText, nullable=True)
    emergency_contact_encrypted: Mapped[str | None] = mapped_column(EncryptedText, nullable=True)

    # ---- Role & permissions ---------------------------------------------- #
    role: Mapped[Role] = mapped_column(
        Enum(Role, name="user_role"),
        default=Role.EMPLOYEE,
        nullable=False,
        index=True,
    )

    employee_id: Mapped[uuid.UUID | None] = mapped_column(
        SQL_UUID(as_uuid=True),
        nullable=True,
        index=True,
    )

    # ---- Account state --------------------------------------------------- #
    is_active: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False, server_default=text("true")
    )
    is_super_admin: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False, server_default=text("false")
    )
    is_demo: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False, server_default=text("false")
    )

    # ---- Password lifecycle ---------------------------------------------- #
    password_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)
    password_changed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )
    must_change_password: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default=text("false"), nullable=False
    )
    last_login_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    last_login_ip: Mapped[str | None] = mapped_column(String(64), nullable=True)

    # Password history for reuse prevention (stored as JSON array of hashes)
    password_history_encrypted: Mapped[str | None] = mapped_column(EncryptedText, nullable=True)

    # ---- Account security (failed attempts, lockout) --------------------- #
    failed_login_attempts: Mapped[int] = mapped_column(
        Integer, default=0, nullable=False, server_default=text("0")
    )
    last_failed_login_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    locked_out_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )
    lockout_reason: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # ---- Two-factor authentication --------------------------------------- #
    totp_secret_encrypted: Mapped[str | None] = mapped_column(
        EncryptedText, nullable=True
    )
    pending_totp_secret_encrypted: Mapped[str | None] = mapped_column(
        EncryptedText, nullable=True
    )
    pending_totp_created_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    two_factor_enabled: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False, index=True,
        server_default=text("false"),
    )
    two_factor_confirmed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    totp_recovery_codes_encrypted: Mapped[str | None] = mapped_column(
        EncryptedText, nullable=True
    )
    mfa_enrollment_required: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default=text("false"), nullable=False, index=True
    )

    # ---- Audit fields ---------------------------------------------------- #
    created_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True,
        server_default=text("now()"), index=True,
    )
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, server_default=text("now()"),
    )

    # ---- Relationships --------------------------------------------------- #
    tenant: Mapped["Tenant | None"] = relationship(
        "Tenant", back_populates="users", foreign_keys="User.tenant_id"
    )
    sessions: Mapped[list["UserSession"]] = relationship(
        "UserSession", back_populates="user", cascade="all, delete-orphan"
    )

    # ---- Computed properties --------------------------------------------- #
    @property
    def password_expired(self) -> bool:
        """True when the password is older than PASSWORD_EXPIRE_DAYS."""
        from app.core.config import settings

        if not settings.PASSWORD_EXPIRATION_ENABLED:
            return False
        if self.password_changed_at is None:
            return False
        return datetime.now(self.password_changed_at.tzinfo) > (  # type: ignore
            self.password_changed_at + timedelta(days=settings.PASSWORD_EXPIRE_DAYS)
        )

    @property
    def password_expires_soon(self) -> bool:
        """True when password will expire within PASSWORD_EXPIRE_WARNING_DAYS."""
        from app.core.config import settings
        from datetime import UTC

        if not settings.PASSWORD_EXPIRATION_ENABLED:
            return False
        if self.password_changed_at is None:
            return False
        warning_at = (
            self.password_changed_at
            + timedelta(days=settings.PASSWORD_EXPIRE_DAYS)
            - timedelta(days=settings.PASSWORD_EXPIRE_WARNING_DAYS)
        )
        return datetime.now(UTC) >= warning_at

    @property
    def requires_password_change(self) -> bool:
        """True when the portal must force a rotation."""
        return bool(self.must_change_password) or self.password_expired

    @property
    def is_locked_out(self) -> bool:
        """True if the account is currently locked out."""
        if self.locked_out_at is None:
            return False
        from app.core.config import settings
        lockout_end = self.locked_out_at + timedelta(minutes=settings.LOCKOUT_DURATION_MINUTES)
        return datetime.now(self.locked_out_at.tzinfo) < lockout_end

    @property
    def effective_roles(self) -> list[str]:
        """All roles for this user (primary role)."""
        primary = self.role.value if hasattr(self.role, "value") else str(self.role)
        return [primary]

    def has_role(self, *role_names: str) -> bool:
        """True if the user holds any of the given roles."""
        if self.is_super_admin:
            return True
        effective = set(self.effective_roles)
        normalized_names = set()
        for name in role_names:
            normalized_names.add(name)
            normalized_names.add(__import__("app.core.role_aliases", fromlist=["normalize_role"]).normalize_role(name))
        return bool(effective.intersection(normalized_names))

    def __repr__(self) -> str:
        return f"<User {self.email!r} (role={self.role})>"


class RoleModel(TenantBase, Base):
    """Tenant-scoped role definition.

    ``code`` mirrors the Role enum value for canonical roles;
    extra tenant-specific roles can also be created.
    """

    __tablename__ = "roles"
    __table_args__ = (
    )

    code: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_system: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False, server_default=text("false")
    )

    permissions: Mapped[list["RolePermission"]] = relationship(
        "RolePermission", back_populates="role", cascade="all, delete-orphan"
    )
    user_links: Mapped[list["UserRole"]] = relationship(
        "UserRole", back_populates="role", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<RoleModel {self.code!r}>"


class Permission(TenantBase, Base):
    """Granular permission (e.g. 'employees.create', 'payroll.publish')."""

    __tablename__ = "permissions"
    __table_args__ = (
    )

    code: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    module: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    action: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)


class RolePermission(UUIDPrimaryKey, Base):
    """Junction table: many-to-many between RoleModel and Permission."""

    __tablename__ = "role_permissions"
    __table_args__ = (
    )

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        SQL_UUID(as_uuid=True), nullable=False, index=True
    )
    role_id: Mapped[uuid.UUID] = mapped_column(
        SQL_UUID(as_uuid=True), ForeignKey("roles.id", ondelete="CASCADE"), nullable=False
    )
    permission_id: Mapped[uuid.UUID] = mapped_column(
        SQL_UUID(as_uuid=True), ForeignKey("permissions.id", ondelete="CASCADE"), nullable=False
    )

    role: Mapped["RoleModel"] = relationship("RoleModel", back_populates="permissions")
    permission: Mapped["Permission"] = relationship("Permission", back_populates="role_links")


class UserRole(TenantBase, Base):
    """Junction table: additional roles assigned to a user.

    A user's primary ``role`` is on the ``User`` row; this table holds
    additional roles (e.g. manager AND employee).
    """

    __tablename__ = "user_roles"
    __table_args__ = (
    )

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        SQL_UUID(as_uuid=True), nullable=False, index=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        SQL_UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    role_id: Mapped[uuid.UUID] = mapped_column(
        SQL_UUID(as_uuid=True), ForeignKey("roles.id", ondelete="CASCADE"), nullable=False
    )

    role: Mapped["RoleModel"] = relationship("RoleModel", back_populates="user_links")


class UserSession(Base):
    """Device session tracked for login/logout and remote session revocation.

    One row per device login. Refresh tokens are hashed and stored; the
    session is revoked when the user logs out or the refresh token is rotated.
    """

    __tablename__ = "user_sessions"
    __table_args__ = (
    )

    id: Mapped[uuid.UUID] = mapped_column(
        SQL_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        SQL_UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        SQL_UUID(as_uuid=True), nullable=False, index=True
    )

    device: Mapped[str | None] = mapped_column(String(255), nullable=True)
    browser: Mapped[str | None] = mapped_column(String(160), nullable=True)
    location: Mapped[str | None] = mapped_column(String(160), nullable=True)
    ip_address: Mapped[str | None] = mapped_column(String(64), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(Text, nullable=True)
    device_fingerprint: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Token tracking
    refresh_token_hash: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    previous_refresh_token_hash: Mapped[str | None] = mapped_column(
        String(128), nullable=True, index=True
    )

    # Session lifecycle
    is_current: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False, server_default=text("true")
    )
    revoked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    last_active_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, server_default=text("now()")
    )

    user: Mapped["User"] = relationship("User", back_populates="sessions")


class PasswordResetToken(Base):
    """Single-use password reset / invitation token."""

    __tablename__ = "password_reset_tokens"
    __table_args__ = (
    )

    id: Mapped[uuid.UUID] = mapped_column(
        SQL_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        SQL_UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    token_hash: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    used_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    requested_ip: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, server_default=text("now()")
    )

    @property
    def is_valid(self) -> bool:
        """True if the token is unused and unexpired."""
        from datetime import UTC

        return self.used_at is None and self.expires_at > datetime.now(UTC)


class EmailVerificationToken(Base):
    """Single-use email verification token."""

    __tablename__ = "email_verification_tokens"
    __table_args__ = (
    )

    id: Mapped[uuid.UUID] = mapped_column(
        SQL_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        SQL_UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    token_hash: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    used_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    requested_ip: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, server_default=text("now()")
    )

    @property
    def is_valid(self) -> bool:
        """True if the token is unused and unexpired."""
        from datetime import UTC

        return self.used_at is None and self.expires_at > datetime.now(UTC)


__all__ = [
    "Tenant",
    "User",
    "RoleModel",
    "Permission",
    "RolePermission",
    "UserRole",
    "UserSession",
    "PasswordResetToken",
    "EmailVerificationToken",
]