"""
Auth service — business logic layer for the auth module.

Contains all authentication business rules and orchestration:
login, token refresh, current-user profile, password change, logout,
two-factor enrollment and MFA verification, password reset flows.

Follows SOLID:
- SRP: only handles auth domain logic; routes stay thin.
- DIP: depends on the repository abstraction (constructor-injected), never
  touches the DB directly.
"""

from __future__ import annotations

import hashlib
import secrets
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import record_audit
from app.core.config import settings
from app.core.dependencies import CurrentUser
from app.core.exceptions import (
    AuthenticationError,
    ConflictError,
    NotFoundError,
    ValidationError,
)
from app.core.lockout import (
    check_login_lockout,
    check_mfa_lockout,
    record_failed_login,
    record_failed_mfa,
    reset_login_failures,
    reset_mfa_failures,
)
from app.core.logging import get_logger
from app.core.password_policy import check_password_strength, generate_temporary_password
from app.core.security import (
    create_access_token,
    create_mfa_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
    revoke_token,
    is_token_revoked,
    revoke_all_for_user,
)
from app.core.totp import (
    generate_totp_secret,
    verify_totp,
    otpauth_uri,
    generate_recovery_codes,
    hash_recovery_codes,
    redeem_recovery_code,
)
from app.core.user_agent import describe_client, parse_user_agent
from app.integrations.email.factory import get_email_sender
from app.integrations.email.contracts import EmailMessage, EmailAddress
from app.models.enums import AuditAction, Role, TenantStatus
from app.models.user import PasswordResetToken, User, UserSession
from app.modules.auth.repository.user_repository import UserRepository
from app.modules.auth.schemas import (
    SessionInfo,
    TokenResponse,
    TwoFactorChallengeResponse,
    TwoFactorConfirmResponse,
    TwoFactorRegenerateResponse,
    TwoFactorResponse,
    TwoFactorSetupResponse,
    UserInfo,
)

logger = get_logger(__name__)


DEMO_PERSONAS: dict[str, tuple[str, Role]] = {
    "platform_owner": ("platform-owner@example.com", Role.PLATFORM_OWNER),
    "platform_admin": ("platform-admin@example.com", Role.PLATFORM_ADMIN),
    "hr_admin": ("hr-admin@example.com", Role.HR_ADMIN),
    "employee": ("employee@example.com", Role.EMPLOYEE),
    "tenant_admin": ("tenant-admin@example.com", Role.TENANT_ADMIN),
}


def _hash_refresh_token(token: str) -> str:
    """SHA-256 hash of a refresh token for storage."""
    import hashlib

    return hashlib.sha256(token.encode()).hexdigest()


class AuthService:
    """Authentication service — login, refresh, MFA, password management."""

    @staticmethod
    def permissions_for(roles: str | list[str]) -> list[str]:
        """Union of permission strings across one or more role codes."""
        from app.core.permissions import ROLE_PERMISSIONS
        from app.core.role_aliases import normalize_role

        if isinstance(roles, str):
            roles = [roles]
        normalized = [normalize_role(r) for r in roles]
        if any(r == Role.PLATFORM_OWNER for r in normalized):
            return ["*"]
        perms: set[str] = set()
        for r in normalized:
            perms |= ROLE_PERMISSIONS.get(r, set())
        return sorted(perms)

    def __init__(self, repo: UserRepository | None = None) -> None:
        self._repo = repo or UserRepository()

    async def _build_user_info(
        self, session: AsyncSession, user: User
    ) -> UserInfo:
        """Assemble the UserInfo payload for a user row."""
        tenant = await self._repo.get_tenant_by_id(session, user.tenant_id)
        effective_roles = sorted({str(r) for r in user.effective_roles})

        # Determine role scopes from the user's role
        role_scopes: list[dict[str, object]] = []
        for role in effective_roles:
            normalized_role = normalize_role(role) if isinstance(role, str) else str(role)
            from app.core.role_aliases import normalize_role as _normalize

            normalized_role = _normalize(role)
            if normalized_role == Role.PLATFORM_OWNER.value:
                role_scopes.append(
                    {"role": normalized_role, "scope_type": "global", "values": []}
                )
            else:
                role_scopes.append(
                    {"role": normalized_role, "scope_type": "tenant", "values": []}
                )

        effective_permissions = self.permissions_for(effective_roles)

        global_permissions = effective_permissions
        if Role.PLATFORM_OWNER.value not in effective_roles:
            pass

        role_precedence = [
            Role.PLATFORM_OWNER,
            Role.PLATFORM_ADMIN,
            Role.PRODUCT_ADMIN,
            Role.BILLING_ADMIN,
            Role.SECURITY_ADMIN,
            Role.SUPPORT_ADMIN,
            Role.PLATFORM_AUDITOR,
        ]
        effective_role = next(
            (r for r in role_precedence if r.value in effective_roles),
            effective_roles[0] if effective_roles else "",
        )
        if isinstance(effective_role, Role):
            effective_role = effective_role.value

        return UserInfo(
            id=user.id,
            email=user.email,
            role=effective_role,
            tenant_id=user.tenant_id,
            tenant_name=tenant.name if tenant else None,
            employee_id=getattr(user, "employee_id", None),
            employee_name=user.name,
            permissions=effective_permissions,
            global_permissions=global_permissions,
            effective_roles=effective_roles,
            base_role=user.role.value if user.role else None,
            effective_role_scopes=role_scopes,
            mfa_enrollment_required=bool(getattr(user, "mfa_enrollment_required", False)),
            must_change_password=bool(getattr(user, "must_change_password", False)),
            password_expired=bool(user.password_expired),
            password_expires_soon=bool(user.password_expires_soon),
            password_changed_at=user.password_changed_at,
        )

    async def _create_session_row(
        self,
        session: AsyncSession,
        user: User,
        refresh_token: str,
        ip_address: str | None,
        user_agent: str | None,
        device_fingerprint: str | None = None,
    ) -> UserSession:
        """Track the device this login came from."""
        client = parse_user_agent(user_agent)
        row = UserSession(
            user_id=user.id,
            tenant_id=user.tenant_id,
            device=client.device,
            browser=describe_client(user_agent),
            location=None,
            ip_address=ip_address,
            user_agent=(user_agent or "")[:2000] or None,
            device_fingerprint=device_fingerprint,
            refresh_token_hash=_hash_refresh_token(refresh_token),
            last_active_at=datetime.now(UTC),
            expires_at=datetime.now(UTC) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
            is_current=True,
        )
        return await self._repo.create_session(session, row)

    async def _issue_login_tokens(
        self,
        session: AsyncSession,
        user: User,
        ip_address: str | None,
        user_agent: str | None,
        device_fingerprint: str | None = None,
    ) -> TokenResponse:
        """Final step of a fully authenticated login: mint tokens + session."""
        # Tenant lifecycle enforcement
        tenant = await self._repo.get_tenant_by_id(session, user.tenant_id)
        if tenant is None:
            raise AuthenticationError(
                "Your organization's account is no longer available. Contact support.",
                error_code="tenant_not_found",
            )
        if tenant.status in (TenantStatus.SUSPENDED, TenantStatus.ARCHIVED):
            state = "suspended" if tenant.status == TenantStatus.SUSPENDED else "archived"
            raise AuthenticationError(
                f"Your organization's account is {state}. Contact support.",
                error_code=f"tenant_{state}",
            )

        from app.core.role_aliases import normalize_role

        effective_roles = sorted({normalize_role(r) for r in user.effective_roles})

        # Build role scopes for the token
        role_scopes: list[dict[str, object]] = []
        for role in effective_roles:
            role_scopes.append(
                {"role": role, "scope_type": "global", "values": []}
            )

        user_info = await self._build_user_info(session, user)
        refresh_token = create_refresh_token(user.id, user.tenant_id)

        await self._repo.update_last_login(session, user.tenant_id, user.id, ip_address)

        session_row = None
        if device_fingerprint:
            session_row = await self._repo.get_active_session_by_device(
                session, user.id, device_fingerprint, datetime.now(UTC)
            )

        if session_row is not None:
            # Same device signing in again — resume the existing session.
            session_row.refresh_token_hash = _hash_refresh_token(refresh_token)
            session_row.ip_address = ip_address
            session_row.user_agent = (user_agent or "")[:2000] or None
            session_row.last_active_at = datetime.now(UTC)
            session_row.expires_at = datetime.now(UTC) + timedelta(
                days=settings.REFRESH_TOKEN_EXPIRE_DAYS
            )
            session_row.is_current = True
            session_row.revoked_at = None
            await session.flush()
            await self._repo.clear_current_flags(session, user.id, session_row.id)
        else:
            # Persist the device session first
            session_row = await self._create_session_row(
                session, user, refresh_token, ip_address, user_agent, device_fingerprint
            )
            await self._repo.clear_current_flags(session, user.id, session_row.id)

        access_token = create_access_token(
            user.id,
            user.tenant_id,
            user.role.value,
            extra_claims={
                "sid": str(session_row.id),
                "roles": effective_roles,
                "role_scopes": role_scopes,
                "mfa_enrollment_required": bool(
                    getattr(user, "mfa_enrollment_required", False)
                ),
            },
        )

        logger.info("Login success: user=%s tenant=%s", user.email, user.tenant_id)
        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            user=user_info,
        )

    async def demo_login(
        self,
        session: AsyncSession,
        persona: str,
        ip_address: str | None = None,
        user_agent: str | None = None,
        device_fingerprint: str | None = None,
    ) -> TokenResponse:
        """Issue a normal session for an allowlisted local demo persona."""
        from app.core.exceptions import NotFoundError

        if settings.ENVIRONMENT not in {"local", "development", "testing"}:
            raise NotFoundError("Demo login is not available.")
        spec = DEMO_PERSONAS.get(persona)
        if spec is None:
            raise NotFoundError("Demo persona not found.")
        email, expected_role = spec
        user = await self._repo.get_by_email_global(session, email)
        tenant = await self._repo.get_tenant_by_id(session, user.tenant_id) if user else None
        if (
            user is None
            or not user.is_active
            or not user.is_demo
            or user.role != expected_role
            or tenant is None
            or not getattr(tenant, "is_platform", False)
            or user.two_factor_enabled
        ):
            raise AuthenticationError("Demo persona is unavailable.")
        logger.info("Demo persona login: persona=%s user=%s", persona, user.id)
        return await self._issue_login_tokens(
            session,
            user,
            ip_address,
            user_agent,
            device_fingerprint,
        )

    async def login(
        self,
        session: AsyncSession,
        email: str,
        password: str,
        ip_address: str | None = None,
        user_agent: str | None = None,
        device_fingerprint: str | None = None,
    ) -> TokenResponse | TwoFactorChallengeResponse:
        """Authenticate a user by email + password and issue JWT tokens."""
        user = await self._repo.get_by_email_global(session, email)
        tenant_id = user.tenant_id if user else None
        user_id = user.id if user else None

        # Lockout check (P0 -100)
        await check_login_lockout(tenant_id, user_id, ip_address)

        if not user or not user.password_hash:
            await record_failed_login(tenant_id, user_id, ip_address)
            raise AuthenticationError("Invalid email or password")

        if not verify_password(password, user.password_hash):
            await record_failed_login(tenant_id, user_id, ip_address)
            raise AuthenticationError("Invalid email or password")

        # Password expiration policy
        if user.password_expired:
            raise AuthenticationError(
                "Your password has expired. Please reset your password to continue.",
                error_code="password_expired",
            )

        # Password verified — clear any failed-login counters.
        await reset_login_failures(tenant_id, user.id, ip_address)

        if user.two_factor_enabled:
            mfa_token = create_mfa_token(
                user.id,
                user.tenant_id,
                user.role.value,
                lifetime_minutes=settings.MFA_TOKEN_EXPIRE_MINUTES,
            )
            logger.info("Login step 1 complete (2FA required): user=%s", user.email)
            return TwoFactorChallengeResponse(
                require_2fa=True,
                mfa_token=mfa_token,
                expires_in=settings.MFA_TOKEN_EXPIRE_MINUTES * 60,
            )

        return await self._issue_login_tokens(
            session, user, ip_address, user_agent, device_fingerprint
        )

    async def refresh(self, session: AsyncSession, refresh_token: str) -> dict[str, str]:
        """Exchange a valid refresh token for a new access token."""
        payload = decode_token(refresh_token)
        if not payload or payload.get("type") != "refresh":
            raise AuthenticationError("Invalid or expired refresh token")

        jti = payload.get("jti")
        if jti and is_token_revoked(jti):
            await self._revoke_family_on_reuse(session, refresh_token)
            raise AuthenticationError("Invalid or expired refresh token")

        user_id = payload.get("sub")
        tenant_id = payload.get("tenant_id")
        if not user_id or not tenant_id:
            raise AuthenticationError("Invalid or expired refresh token")

        token_hash = _hash_refresh_token(refresh_token)
        session_row = await self._repo.get_session_by_refresh_hash(session, token_hash)

        if session_row is None:
            previous = await self._repo.get_session_by_previous_refresh_hash(session, token_hash)
            if previous is not None and previous.revoked_at is None:
                await self._repo.revoke_session(session, previous.id)
                await session.commit()
                logger.warning(
                    "Refresh-token replay detected — session family revoked: user=%s session=%s",
                    previous.user_id,
                    previous.id,
                )
            raise AuthenticationError("Session revoked or expired — sign in again")

        user = await self._repo.get_by_id_global(session, UUID(tenant_id))
        if not user or not user.is_active:
            raise AuthenticationError("User no longer active")

        tenant_row = await self._repo.get_tenant_by_id(session, user.tenant_id)
        if tenant_row is not None and tenant_row.status == TenantStatus.SUSPENDED:
            raise AuthenticationError(
                "Your organization's account is suspended. Contact support.",
                error_code="tenant_suspended",
            )

        now = datetime.now(UTC)
        effective_roles = sorted(
            {normalize_role(r) for r in user.effective_roles}
        )
        result: dict[str, str]

        if session_row.revoked_at is not None or session_row.expires_at <= now:
            raise AuthenticationError("Session revoked or expired")

        if settings.REFRESH_TOKEN_ROTATION_ENABLED:
            if jti and payload.get("exp"):
                revoke_token(jti, int(payload["exp"]))

            if settings.REFRESH_TOKEN_SLIDING_EXPIRATION:
                candidate = now + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
                absolute_cap = session_row.created_at + timedelta(
                    days=settings.SESSION_ABSOLUTE_MAX_DAYS
                )
                session_row.expires_at = min(candidate, absolute_cap)

            new_refresh_token = create_refresh_token(
                user.id, user.tenant_id, expires_at=session_row.expires_at
            )

            session_row.previous_refresh_token_hash = token_hash
            session_row.refresh_token_hash = _hash_refresh_token(new_refresh_token)
            session_row.last_active_at = now
            await session.flush()

            access_token = create_access_token(
                user.id,
                user.tenant_id,
                user.role.value,
                extra_claims={
                    "sid": str(session_row.id),
                    "roles": effective_roles,
                    "role_scopes": [],
                    "mfa_enrollment_required": bool(
                        getattr(user, "mfa_enrollment_required", False)
                    ),
                },
            )
            result = {
                "access_token": access_token,
                "refresh_token": new_refresh_token,
                "token_type": "bearer",
            }
            logger.info("Refresh token rotated: user=%s session=%s", user.id, session_row.id)
        else:
            await self._repo.touch_session(session, session_row.id)
            access_token = create_access_token(
                user.id,
                user.tenant_id,
                user.role.value,
                extra_claims={
                    "sid": str(session_row.id),
                    "roles": effective_roles,
                    "mfa_enrollment_required": bool(
                        getattr(user, "mfa_enrollment_required", False)
                    ),
                },
            )
            result = {"access_token": access_token, "token_type": "bearer"}

        return result

    async def _revoke_family_on_reuse(
        self,
        session: AsyncSession,
        refresh_token: str,
    ) -> None:
        """Revoke the session a blacklisted refresh token belongs to."""
        token_hash = _hash_refresh_token(refresh_token)
        session_row = await self._repo.get_session_by_refresh_hash(session, token_hash)
        if session_row is None:
            session_row = await self._repo.get_session_by_previous_refresh_hash(session, token_hash)
        if session_row is not None and session_row.revoked_at is None:
            await self._repo.revoke_session(session, session_row.id)
            await session.commit()
            logger.warning(
                "Revoked session %s after reuse of blacklisted refresh token",
                session_row.id,
            )

    async def get_me(self, session: AsyncSession, user: CurrentUser) -> UserInfo:
        """Return the current user's profile + effective permissions."""
        db_user = await self._repo.get_by_id(session, user.tenant_id, user.id)
        if not db_user:
            raise AuthenticationError("User not found")
        return await self._build_user_info(session, db_user)

    # ---- Two-factor authentication (TOTP) ---------------------------------- #

    @staticmethod
    def _verify_user_code(user: User, token: str) -> bool:
        """Verify a TOTP or one-time recovery code against a user row.

        When a recovery code is used its hash is removed from the user's
        stored list (single-use). Returns True on success.
        """
        if verify_totp(user.totp_secret_encrypted or "", token):
            return True
        remaining = redeem_recovery_code(user.totp_recovery_codes_encrypted or "", token)
        if remaining is not None:
            user.totp_recovery_codes_encrypted = remaining
            return True
        return False

    async def complete_mfa_login(
        self,
        session: AsyncSession,
        mfa_token: str,
        token: str,
        ip_address: str | None = None,
        user_agent: str | None = None,
        device_fingerprint: str | None = None,
    ) -> TokenResponse:
        """Complete a password login that required 2FA."""
        payload = decode_token(mfa_token)
        if not payload or payload.get("type") != "mfa":
            raise AuthenticationError("MFA challenge expired — sign in again")

        jti = payload.get("jti")
        if jti and is_token_revoked(jti):
            raise AuthenticationError("MFA challenge already used — sign in again")

        user_id = payload.get("sub")
        tenant_id = payload.get("tenant_id")
        if not user_id or not tenant_id:
            raise AuthenticationError("MFA challenge expired — sign in again")

        user = await self._repo.get_by_id_global(session, UUID(tenant_id))
        if not user or not user.is_active or not user.two_factor_enabled:
            raise AuthenticationError("Account not available — sign in again")

        # MFA lockout check
        await check_mfa_lockout(tenant_id, user.id, ip_address)

        if not self._verify_user_code(user, token):
            await record_failed_mfa(tenant_id, user.id, ip_address)
            raise AuthenticationError("Invalid verification code")

        await reset_mfa_failures(tenant_id, user.id, ip_address)

        # Single-use: burn the challenge
        if jti and payload.get("exp"):
            revoke_token(jti, int(payload["exp"]))
        await session.commit()

        return await self._issue_login_tokens(
            session, user, ip_address, user_agent, device_fingerprint
        )

    async def get_two_factor_status(
        self, session: AsyncSession, user: CurrentUser
    ) -> TwoFactorResponse:
        """Return the user's 2FA status, including any pending setup."""
        db_user = await self._repo.get_by_id(session, user.tenant_id, user.id)
        if not db_user:
            raise AuthenticationError("User not found")

        pending_expires_at = None
        if db_user.pending_totp_secret_encrypted and db_user.pending_totp_created_at:
            pending_expires_at = db_user.pending_totp_created_at + timedelta(
                minutes=settings.TWO_FACTOR_PENDING_TIMEOUT_MINUTES
            )
            if pending_expires_at <= datetime.now(UTC):
                db_user.pending_totp_secret_encrypted = None
                db_user.pending_totp_created_at = None
                await session.commit()
                pending_expires_at = None

        return TwoFactorResponse(
            two_factor_enabled=bool(db_user.two_factor_enabled),
            pending_setup=pending_expires_at is not None,
            pending_expires_at=pending_expires_at,
        )

    async def setup_two_factor(
        self, session: AsyncSession, user: CurrentUser
    ) -> TwoFactorSetupResponse:
        """Begin enrolling an authenticator app."""
        db_user = await self._repo.get_by_id(session, user.tenant_id, user.id)
        if not db_user:
            raise AuthenticationError("User not found")
        if db_user.two_factor_enabled:
            raise ConflictError("Two-factor authentication is already enabled.")

        secret = generate_totp_secret()
        db_user.pending_totp_secret_encrypted = secret
        db_user.pending_totp_created_at = datetime.now(UTC)
        await session.commit()

        account = db_user.email
        issuer = settings.TWO_FACTOR_ISSUER
        uri = otpauth_uri(secret, account, issuer)

        # Generate QR SVG
        from app.core.security import _render_qr_svg

        qr_svg = _render_qr_svg(uri)

        return TwoFactorSetupResponse(
            secret=secret,
            otpauth_uri=uri,
            qr_svg=qr_svg,
            account=account,
            issuer=issuer,
        )

    async def confirm_two_factor(
        self, session: AsyncSession, user: CurrentUser, token: str
    ) -> TwoFactorConfirmResponse:
        """Confirm setup by verifying a code from the authenticator app."""
        db_user = await self._repo.get_by_id(session, user.tenant_id, user.id)
        if not db_user:
            raise AuthenticationError("User not found")
        if db_user.two_factor_enabled:
            raise ConflictError("Two-factor authentication is already enabled.")

        pending = db_user.pending_totp_secret_encrypted
        if not pending:
            raise ValidationError("No pending 2FA setup. Start again.")

        created_at = db_user.pending_totp_created_at
        if created_at is None or (datetime.now(UTC) - created_at) > timedelta(
            minutes=settings.TWO_FACTOR_PENDING_TIMEOUT_MINUTES
        ):
            db_user.pending_totp_secret_encrypted = None
            db_user.pending_totp_created_at = None
            await session.commit()
            raise ValidationError("Setup expired — please try again.")

        if not verify_totp(pending, token):
            raise AuthenticationError("Invalid verification code")

        recovery_codes = generate_recovery_codes()
        db_user.totp_secret_encrypted = pending
        db_user.totp_recovery_codes_encrypted = hash_recovery_codes(recovery_codes)
        db_user.two_factor_enabled = True
        db_user.mfa_enrollment_required = False
        db_user.two_factor_confirmed_at = datetime.now(UTC)
        db_user.pending_totp_secret_encrypted = None
        db_user.pending_totp_created_at = None
        await session.commit()

        logger.info("2FA enabled: user=%s", db_user.id)
        return TwoFactorConfirmResponse(
            two_factor_enabled=True,
            recovery_codes=recovery_codes,
        )

    async def disable_two_factor(
        self, session: AsyncSession, user: CurrentUser, token: str
    ) -> dict[str, str]:
        """Disable 2FA — requires a valid TOTP or recovery code first."""
        db_user = await self._repo.get_by_id(session, user.tenant_id, user.id)
        if not db_user:
            raise AuthenticationError("User not found")
        if not db_user.two_factor_enabled:
            raise ValidationError("Two-factor authentication is not enabled.")

        if not self._verify_user_code(db_user, token):
            raise AuthenticationError("Invalid verification code")

        db_user.totp_secret_encrypted = None
        db_user.totp_recovery_codes_encrypted = None
        db_user.two_factor_enabled = False
        db_user.two_factor_confirmed_at = None
        db_user.pending_totp_secret_encrypted = None
        db_user.pending_totp_created_at = None
        await session.commit()

        logger.info("2FA disabled: user=%s", db_user.id)
        return {"message": "Two-factor authentication disabled."}

    async def regenerate_recovery_codes(
        self, session: AsyncSession, user: CurrentUser, token: str
    ) -> TwoFactorRegenerateResponse:
        """Replace all recovery codes — old ones are revoked immediately."""
        db_user = await self._repo.get_by_id(session, user.tenant_id, user.id)
        if not db_user:
            raise AuthenticationError("User not found")
        if not db_user.two_factor_enabled or not db_user.totp_secret_encrypted:
            raise ValidationError("Two-factor authentication is not enabled.")

        if not self._verify_user_code(db_user, token):
            raise AuthenticationError("Invalid verification code")

        new_codes = generate_recovery_codes()
        db_user.totp_recovery_codes_encrypted = hash_recovery_codes(new_codes)
        await session.commit()

        logger.info("Recovery codes regenerated: user=%s", db_user.id)
        return TwoFactorRegenerateResponse(recovery_codes=new_codes)

    async def change_password(
        self,
        session: AsyncSession,
        user: CurrentUser,
        current_password: str,
        new_password: str,
    ) -> dict[str, str]:
        """Change the current user's password."""
        db_user = await self._repo.get_by_id(session, user.tenant_id, user.id)
        if not db_user or not db_user.password_hash:
            raise AuthenticationError("User not found")

        if not verify_password(current_password, db_user.password_hash):
            raise AuthenticationError("Current password is incorrect")

        strength = check_password_strength(new_password)
        if not strength.is_strong:
            raise ValidationError(
                "Password does not meet security requirements.",
                new_password="; ".join(strength.suggestions) or "Password is too weak.",
                score=strength.score,
            )

        await self._repo.update_password(
            session, user.tenant_id, user.id, hash_password(new_password)
        )
        await self._repo.revoke_all_sessions(session, user.id)
        await session.commit()

        # Best-effort sweep: blacklist outstanding JWTs for this user.
        revoke_all_for_user(user_id=str(user.id))

        logger.info("Password changed: user=%s", user.id)
        return {
            "message": "Password changed successfully. All sessions have been "
            "revoked — please sign in again."
        }

    # ---- Forgot / reset password ---------------------------------------------- #

    async def request_password_reset(
        self, session: AsyncSession, email: str, ip_address: str | None = None
    ) -> dict[str, str]:
        """Email a single-use password-reset link."""
        user = await self._repo.get_by_email_global(session, email)
        if user:
            raw_token = secrets.token_urlsafe(32)
            reset_row = PasswordResetToken(
                user_id=user.id,
                token_hash=_hash_reset_token(raw_token),
                expires_at=datetime.now(UTC)
                + timedelta(minutes=settings.PASSWORD_RESET_TOKEN_EXPIRE_MINUTES),
                requested_ip=ip_address,
            )
            await self._repo.create_reset_token(session, reset_row)
            await session.commit()

            reset_url = f"{settings.FRONTEND_BASE_URL.rstrip('/')}/reset-password?token={raw_token}"
            try:
                from_email = EmailAddress(
                    email=settings.NOTIFICATIONS_FROM_EMAIL or user.email,
                    name=settings.NOTIFICATIONS_FROM_NAME or settings.APP_NAME,
                )
                await get_email_sender().send(
                    EmailMessage(
                        subject="Reset your password",
                        text_content=(
                            f"Hi,\n\n"
                            "We received a request to reset your password.\n"
                            "Open the link below to choose a new password "
                            f"(valid for {settings.PASSWORD_RESET_TOKEN_EXPIRE_MINUTES} "
                            "minutes):\n\n"
                            f"{reset_url}\n\n"
                            "If you did not request this, you can safely ignore this "
                            "email — your password will not change.\n\n"
                            "— Universal FastAPI Foundation"
                        ),
                        from_email=from_email,
                        to_emails=[EmailAddress(email=user.email)],
                    )
                )
            except Exception as exc:
                logger.error("Failed to send password-reset email: %s", exc)
                raise ValidationError(
                    "Could not send the reset email. Please try again later."
                ) from exc

            logger.info("Password reset requested: user=%s ip=%s", user.id, ip_address)
        else:
            logger.info("Password reset requested for unknown email=%s", email)

        return {"message": "If an account with that email exists, a reset link has been sent."}

    async def reset_password(
        self,
        session: AsyncSession,
        token: str,
        new_password: str,
        ip_address: str | None = None,
    ) -> dict[str, str]:
        """Consume a reset token and set a new password."""
        if not token:
            raise ValidationError("Reset token is required.")

        now = datetime.now(UTC)
        reset_row = await self._repo.get_valid_reset_token(session, _hash_reset_token(token), now)
        if reset_row is None:
            raise ValidationError("Invalid or expired reset token.")

        strength = check_password_strength(new_password)
        if not strength.is_strong:
            raise ValidationError(
                "Password does not meet security requirements.",
                new_password="; ".join(strength.suggestions) or "Password is too weak.",
                score=strength.score,
            )

        user = await session.get(User, reset_row.user_id)
        if user is None or not user.is_active:
            raise ValidationError("Invalid or expired reset token.")

        await self._repo.update_password(
            session, user.tenant_id, user.id, hash_password(new_password)
        )
        await self._repo.mark_reset_token_used(session, reset_row.id)
        await self._repo.revoke_all_sessions(session, user.id)
        await session.commit()

        revoke_all_for_user(user_id=str(user.id))

        logger.info("Password reset completed: user=%s ip=%s", user.id, ip_address)
        return {"message": "Password reset successful. All sessions have been signed out."}

    async def accept_invitation(
        self,
        session: AsyncSession,
        token: str,
        new_password: str,
        ip_address: str | None = None,
    ) -> dict[str, str]:
        """Consume a tenant-admin invitation token and set the first password."""
        if not token:
            raise ValidationError("Invitation token is required.")

        now = datetime.now(UTC)
        reset_row = await self._repo.get_valid_reset_token(session, _hash_reset_token(token), now)
        if reset_row is None:
            raise ValidationError("Invalid or expired invitation token.")

        strength = check_password_strength(new_password)
        if not strength.is_strong:
            raise ValidationError(
                "Password does not meet security requirements.",
                new_password="; ".join(strength.suggestions) or "Password is too weak.",
                score=strength.score,
            )

        user = await session.get(User, reset_row.user_id)
        if user is None or not user.is_active:
            raise ValidationError("Invalid or expired invitation token.")
        if user.password_hash:
            raise ValidationError(
                "This invitation has already been accepted — use forgot-password instead."
            )

        await self._repo.update_password(
            session, user.tenant_id, user.id, hash_password(new_password)
        )
        await self._repo.mark_reset_token_used(session, reset_row.id)
        await session.commit()

        await record_audit(
            session=session,
            tenant_id=user.tenant_id,
            actor_user_id=user.id,
            action=AuditAction.UPDATE,
            resource="user",
            resource_id=str(user.id),
            description=f"INVITATION_ACCEPTED — invitation accepted for {user.email}",
        )

        logger.info("Invitation accepted: user=%s ip=%s", user.id, ip_address)
        return {"message": "Account activated. You can now sign in with your new password."}

    async def logout(
        self,
        session: AsyncSession,
        access_token: str | None = None,
        refresh_token: str | None = None,
    ) -> dict[str, str]:
        """Revoke the presented tokens and their device session."""
        revoked = 0

        if access_token:
            payload = decode_token(access_token)
            if payload and payload.get("jti") and payload.get("exp"):
                revoke_token(payload["jti"], int(payload["exp"]))
                revoked += 1

        if refresh_token:
            refresh_payload = decode_token(refresh_token)
            if refresh_payload and refresh_payload.get("jti") and refresh_payload.get("exp"):
                revoke_token(refresh_payload["jti"], int(refresh_payload["exp"]))
                revoked += 1

            # Revoke the device session tied to this refresh token.
            session_row = await self._repo.get_session_by_refresh_hash(
                session, _hash_refresh_token(refresh_token)
            )
            if session_row and session_row.revoked_at is None:
                await self._repo.revoke_session(session, session_row.id)
                revoked += 1

        if revoked == 0:
            raise AuthenticationError("Invalid or expired token")

        return {"message": "Logged out successfully."}

    async def logout_all(
        self,
        session: AsyncSession,
        access_token: str | None = None,
        refresh_token: str | None = None,
    ) -> dict[str, str]:
        """Sign the user out of every device (including this one)."""
        revoked_count = 0
        if access_token:
            payload = decode_token(access_token)
            if payload:
                revoked_count += await self._extract_user_id_and_revoke_all(session, payload)
        elif refresh_token:
            payload = decode_token(refresh_token)
            if payload:
                revoked_count += await self._extract_user_id_and_revoke_all(session, payload)

        if access_token:
            payload = decode_token(access_token)
            if payload and payload.get("jti") and payload.get("exp"):
                revoke_token(payload["jti"], int(payload["exp"]))
                revoked_count += 1
        if refresh_token:
            payload = decode_token(refresh_token)
            if payload and payload.get("jti") and payload.get("exp"):
                revoke_token(payload["jti"], int(payload["exp"]))
                revoked_count += 1

        logger.info("Logout-all completed: %s item(s) revoked", revoked_count)
        return {"message": "Logged out from all devices."}

    async def _extract_user_id_and_revoke_all(
        self, session: AsyncSession, payload: dict[str, Any]
    ) -> int:
        """Revoke every session owned by the ``sub`` of a decoded JWT."""
        user_id = payload.get("sub")
        if not user_id:
            return 0
        return await self._repo.revoke_all_sessions(session, UUID(user_id))

    # ---- Sessions (device tracking / remote revocation) ---------------------- #

    async def list_sessions(
        self, session: AsyncSession, user: CurrentUser
    ) -> list[SessionInfo]:
        """Active sessions for the current user."""
        rows = await self._repo.list_active_sessions(session, user.id, datetime.now(UTC))
        current_sid = getattr(user, "session_id", None)
        return [
            SessionInfo(
                id=s.id,
                device=s.device,
                browser=s.browser,
                location=s.location,
                ip_address=s.ip_address,
                last_active_at=s.last_active_at,
                expires_at=s.expires_at,
                is_current=(s.id == current_sid) if current_sid else bool(s.is_current),
                created_at=s.created_at,
            )
            for s in rows
        ]

    async def revoke_device_session(
        self, session: AsyncSession, user: CurrentUser, session_id: UUID
    ) -> dict[str, str]:
        """Revoke one of the current user's sessions."""
        from app.core.exceptions import NotFoundError

        session_row = await self._repo.get_session_by_id(session, user.id, session_id)
        if session_row is None or session_row.revoked_at is not None:
            raise NotFoundError("Session not found")

        await self._repo.revoke_session(session, session_row.id)
        await session.commit()

        logger.info("Session revoked: user=%s session=%s", user.id, session_id)
        return {"message": "Session revoked"}

    async def revoke_other_device_sessions(
        self, session: AsyncSession, user: CurrentUser, keep_session_id: UUID | None = None
    ) -> dict[str, str]:
        """Revoke every other device session."""
        count = await self._repo.revoke_other_sessions(
            session, user.id, keep_session_id=keep_session_id
        )
        await session.commit()
        return {"message": f"Revoked {count} session(s)"}


def _hash_reset_token(token: str) -> str:
    """SHA-256 hash of a reset token for storage."""
    import hashlib

    return hashlib.sha256(token.encode()).hexdigest()


from app.core.role_aliases import normalize_role


def get_auth_service() -> AuthService:
    """FastAPI dependency — per-request AuthService instance."""
    return AuthService()


__all__ = ["AuthService", "get_auth_service", "DEMO_PERSONAS"]
