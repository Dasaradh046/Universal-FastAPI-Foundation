"""
Auth repository — data-access layer for authentication flows.

Handles user lookup, session tracking, password reset tokens, and tenant
resolution. All queries are tenant-scoped unless explicitly documented.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import select, update, func, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.core.security import hash_password
from app.models.user import User, UserSession, PasswordResetToken, EmailVerificationToken
from app.models.enums import Role

logger = get_logger(__name__)


class UserRepository:
    """Data-access layer for the auth module."""

    model = User

    # ---- Lookups ----------------------------------------------------------- #

    async def get_by_email(
        self, session: AsyncSession, tenant_id: UUID, email: str
    ) -> User | None:
        """Tenant-scoped lookup by email (active users only)."""
        stmt = select(User).where(
            User.tenant_id == tenant_id,
            User.email == email,
            User.is_active == True,
        )
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_email_global(self, session: AsyncSession, email: str) -> User | None:
        """Cross-tenant lookup by email — used by login.

        ``email`` is unique per tenant (not globally), so at login time we do
        not yet know the tenant. This method is fail-closed: when the same email
        maps to more than one *active* account across tenants, the login is
        refused (returns None → caller raises the generic "Invalid email or
        password").
        """
        stmt = select(User).where(
            User.email == email,
            User.is_active == True,
        )
        result = (await session.execute(stmt)).scalars().all()
        if len(result) != 1:
            if len(result) > 1:
                logger.warning(
                    "Login refused: email %s maps to %d active accounts across tenants",
                    email,
                    len(result),
                )
            return None
        return result[0]

    async def get_by_id(
        self, session: AsyncSession, tenant_id: UUID, user_id: UUID
    ) -> User | None:
        """Tenant-scoped lookup by user ID."""
        stmt = select(User).where(
            User.id == user_id,
            User.tenant_id == tenant_id,
        )
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_id_global(self, session: AsyncSession, user_id: UUID) -> User | None:
        """Global lookup by user ID (used by token refresh/me)."""
        stmt = select(User).where(User.id == user_id)
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_tenant_by_id(self, session: AsyncSession, tenant_id: UUID):
        """Resolve the Tenant row."""
        from app.models.user import Tenant

        stmt = select(Tenant).where(Tenant.id == tenant_id)
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    async def count_active_super_admins(self, session: AsyncSession) -> int:
        """Count active super-admin users (platform-wide)."""
        stmt = select(func.count()).where(
            User.is_super_admin == True,
            User.is_active == True,
        )
        result = await session.execute(stmt)
        return int(result.scalar_one())

    # ---- Mutations ---------------------------------------------------------- #

    async def update_password(
        self,
        session: AsyncSession,
        tenant_id: UUID,
        user_id: UUID,
        password_hash: str,
        must_change_password: bool = False,
    ) -> User | None:
        """Persist a new password hash."""
        values: dict = {
            "password_hash": password_hash,
            "password_changed_at": datetime.now(UTC),
            "must_change_password": must_change_password,
        }
        stmt = (
            update(User)
            .where(User.id == user_id, User.tenant_id == tenant_id)
            .values(**values)
            .returning(User)
        )
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    async def update_last_login(
        self,
        session: AsyncSession,
        tenant_id: UUID,
        user_id: UUID,
        ip_address: str | None = None,
    ) -> None:
        """Stamp the successful-login audit fields."""
        stmt = (
            update(User)
            .where(User.id == user_id, User.tenant_id == tenant_id)
            .values(
                last_login_at=datetime.now(UTC),
                last_login_ip=ip_address,
            )
        )
        await session.execute(stmt)

    async def set_active(self, session: AsyncSession, user: User, is_active: bool) -> User:
        """Activate or deactivate a user account."""
        user.is_active = is_active
        await session.flush()
        return user

    async def set_password(
        self,
        session: AsyncSession,
        user_id: UUID,
        password_hash: str,
        must_change_password: bool = False,
    ) -> None:
        """Set a password hash for a user (global)."""
        # Get current password history
        user = await self.get_by_id_global(session, user_id)
        if user and user.password_history_encrypted:
            # TODO: Implement proper password history management with encryption
            pass
            
        stmt = (
            update(User)
            .where(User.id == user_id)
            .values(
                password_hash=password_hash,
                password_changed_at=datetime.now(UTC),
                must_change_password=must_change_password,
            )
        )
        await session.execute(stmt)

    # ---- User sessions (device tracking) ------------------------------------ #

    async def create_session(
        self, session: AsyncSession, session_row: UserSession
    ) -> UserSession:
        """Persist a new UserSession row."""
        session.add(session_row)
        await session.flush()
        return session_row

    async def get_session_by_refresh_hash(
        self, session: AsyncSession, refresh_token_hash: str
    ) -> UserSession | None:
        """Find the session row whose refresh-token hash matches."""
        stmt = select(UserSession).where(
            UserSession.refresh_token_hash == refresh_token_hash
        )
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_session_by_previous_refresh_hash(
        self, session: AsyncSession, previous_hash: str
    ) -> UserSession | None:
        """Find session whose previous (rotated-out) refresh token hash matches."""
        stmt = select(UserSession).where(
            UserSession.previous_refresh_token_hash == previous_hash
        )
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_active_session_by_device(
        self, session: AsyncSession, user_id: UUID, device_fingerprint: str, now: datetime
    ) -> UserSession | None:
        """Find a live session for ``user_id`` on the same device."""
        stmt = (
            select(UserSession)
            .where(
                UserSession.user_id == user_id,
                UserSession.device_fingerprint == device_fingerprint,
                UserSession.revoked_at.is_(None),
                UserSession.expires_at > now,
            )
            .order_by(UserSession.last_active_at.desc())
            .limit(1)
        )
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_session_by_id(
        self, session: AsyncSession, user_id: UUID, session_id: UUID
    ) -> UserSession | None:
        """Session lookup scoped to owner."""
        stmt = select(UserSession).where(
            UserSession.id == session_id, UserSession.user_id == user_id
        )
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_active_sessions(
        self, session: AsyncSession, user_id: UUID, now: datetime
    ) -> list[UserSession]:
        """All non-revoked, non-expired sessions for a user, newest first."""
        stmt = (
            select(UserSession)
            .where(
                UserSession.user_id == user_id,
                UserSession.revoked_at.is_(None),
                UserSession.expires_at > now,
            )
            .order_by(UserSession.last_active_at.desc())
        )
        result = await session.execute(stmt)
        return list(result.scalars().all())

    async def touch_session(self, session: AsyncSession, session_id: UUID) -> None:
        """Update ``last_active_at`` (called on every successful refresh)."""
        stmt = (
            update(UserSession)
            .where(UserSession.id == session_id)
            .values(last_active_at=datetime.now(UTC))
        )
        await session.execute(stmt)

    async def clear_current_flags(
        self, session: AsyncSession, user_id: UUID, keep_session_id: UUID
    ) -> None:
        """Unset ``is_current=True`` on every *other* active session for the user."""
        now = datetime.now(UTC)
        stmt = (
            update(UserSession)
            .where(
                UserSession.user_id == user_id,
                UserSession.id != keep_session_id,
                UserSession.revoked_at.is_(None),
                UserSession.expires_at > now,
            )
            .values(is_current=False)
        )
        await session.execute(stmt)

    async def revoke_session(self, session: AsyncSession, session_id: UUID) -> None:
        """Mark a single session revoked."""
        stmt = (
            update(UserSession)
            .where(UserSession.id == session_id)
            .values(revoked_at=datetime.now(UTC), is_current=False)
        )
        await session.execute(stmt)

    async def revoke_other_sessions(
        self, session: AsyncSession, user_id: UUID, keep_session_id: UUID | None = None
    ) -> int:
        """Revoke every active session for ``user_id`` (optionally keeping one)."""
        now = datetime.now(UTC)
        stmt = (
            update(UserSession)
            .where(
                UserSession.user_id == user_id,
                UserSession.revoked_at.is_(None),
            )
            .values(revoked_at=now, is_current=False)
        )
        if keep_session_id is not None:
            stmt = stmt.where(UserSession.id != keep_session_id)
        result = await session.execute(stmt)
        rowcount = getattr(result, "rowcount", 0)
        return int(rowcount or 0)

    async def revoke_all_sessions(self, session: AsyncSession, user_id: UUID) -> int:
        """Revoke *every* session for ``user_id`` including the current one."""
        return await self.revoke_other_sessions(session, user_id, keep_session_id=None)

    # ---- Email verification tokens ------------------------------------------- #

    async def create_email_verification_token(
        self, session: AsyncSession, email_token: EmailVerificationToken
    ) -> EmailVerificationToken:
        """Persist an email verification token, invalidating any earlier unused ones for the user."""
        await session.execute(
            update(EmailVerificationToken)
            .where(
                EmailVerificationToken.user_id == email_token.user_id,
                EmailVerificationToken.used_at.is_(None),
            )
            .values(expires_at=datetime.now(UTC))
        )
        session.add(email_token)
        await session.flush()
        return email_token

    async def get_valid_email_verification_token(
        self, session: AsyncSession, token_hash: str, now: datetime
    ) -> EmailVerificationToken | None:
        """Return the email verification token for ``token_hash`` if unused and unexpired."""
        stmt = select(EmailVerificationToken).where(
            EmailVerificationToken.token_hash == token_hash
        )
        result = await session.execute(stmt)
        token = result.scalar_one_or_none()
        if token is None or not token.is_valid:
            return None
        return token

    async def mark_email_verification_token_used(
        self, session: AsyncSession, token_id: UUID
    ) -> None:
        """Consume a single-use email verification token."""
        stmt = (
            update(EmailVerificationToken)
            .where(EmailVerificationToken.id == token_id)
            .values(used_at=datetime.now(UTC))
        )
        await session.execute(stmt)

    # ---- Password reset tokens (forgot-password flow) ------------------------ #

    async def create_reset_token(
        self, session: AsyncSession, reset_token: PasswordResetToken
    ) -> PasswordResetToken:
        """Persist a reset token, invalidating any earlier unused ones for the user."""
        await session.execute(
            update(PasswordResetToken)
            .where(
                PasswordResetToken.user_id == reset_token.user_id,
                PasswordResetToken.used_at.is_(None),
            )
            .values(expires_at=datetime.now(UTC))
        )
        session.add(reset_token)
        await session.flush()
        return reset_token

    async def get_valid_reset_token(
        self, session: AsyncSession, token_hash: str, now: datetime
    ) -> PasswordResetToken | None:
        """Return the reset token for ``token_hash`` if unused and unexpired."""
        stmt = select(PasswordResetToken).where(
            PasswordResetToken.token_hash == token_hash
        )
        result = await session.execute(stmt)
        token = result.scalar_one_or_none()
        if token is None or not token.is_valid:
            return None
        return token

    async def mark_reset_token_used(
        self, session: AsyncSession, token_id: UUID
    ) -> None:
        """Consume a single-use reset token."""
        stmt = (
            update(PasswordResetToken)
            .where(PasswordResetToken.id == token_id)
            .values(used_at=datetime.now(UTC))
        )
        await session.execute(stmt)


__all__ = ["UserRepository"]
