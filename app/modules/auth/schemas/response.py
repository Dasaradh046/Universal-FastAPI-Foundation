"""
Auth module schemas — login, tokens, MFA, password management.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field

from app.schemas.base import ORMBase


class LoginRequest(BaseModel):
    """Login request body."""

    email: EmailStr = Field(..., description="User email address")
    password: str = Field(..., min_length=6, max_length=128, description="User password")
    device_fingerprint: str | None = Field(
        None,
        min_length=8,
        max_length=128,
        description=(
            "Stable client-generated device identifier. Lets the backend "
            "recognise the same device across logins."
        ),
    )


class DemoLoginRequest(BaseModel):
    """Local/dev-only persona selection."""

    persona: str = Field(
        ...,
        min_length=3,
        max_length=64,
        pattern=r"^[a-z0-9_-]+$",
    )
    device_fingerprint: str | None = Field(None, min_length=8, max_length=128)


class RefreshTokenRequest(BaseModel):
    """Refresh token request body."""

    refresh_token: str | None = None


class ChangePasswordRequest(BaseModel):
    """Change password request."""

    current_password: str = Field(..., min_length=6)
    new_password: str = Field(..., min_length=8, max_length=128)


class ForgotPasswordRequest(BaseModel):
    """POST /auth/forgot-password request body."""

    email: EmailStr = Field(..., description="Account email to send the reset link to")


class ResetPasswordRequest(BaseModel):
    """POST /auth/reset-password request body."""

    token: str = Field(
        ..., min_length=16, max_length=256, description="Reset token from the email link"
    )
    new_password: str = Field(..., min_length=8, max_length=128, description="New password")


class LogoutRequest(BaseModel):
    """Logout request body (refresh token optional)."""

    refresh_token: str | None = Field(None, description="Refresh token to revoke")


class TwoFactorConfirmRequest(BaseModel):
    """POST /auth/2fa/confirm — confirm a pending setup with the current code."""

    token: str = Field(
        ..., min_length=6, max_length=10, description="6-digit TOTP from the authenticator app"
    )


class TwoFactorDisableRequest(BaseModel):
    """POST /auth/2fa/disable — disable 2FA."""

    token: str = Field(
        ...,
        min_length=6,
        max_length=10,
        description="6-digit TOTP or a 10-char recovery code",
    )


class TwoFactorRegenerateRequest(BaseModel):
    """POST /auth/2fa/regenerate — issue a fresh set of recovery codes."""

    token: str = Field(
        ...,
        min_length=6,
        max_length=10,
        description="6-digit TOTP (or an existing recovery code) to authorize",
    )


class TwoFactorVerifyRequest(BaseModel):
    """POST /auth/2fa/verify — complete a login that required 2FA."""

    mfa_token: str = Field(..., description="MFA step-up JWT from the login challenge")
    token: str = Field(
        ...,
        min_length=6,
        max_length=10,
        description="6-digit TOTP from the authenticator app, or a recovery code",
    )
    device_fingerprint: str | None = Field(
        None,
        min_length=8,
        max_length=128,
    )


class UserInfo(ORMBase):
    """User info returned in token response and /me endpoint."""

    id: UUID
    email: str
    role: str
    tenant_id: UUID
    tenant_name: str | None = None
    employee_id: UUID | None = None
    employee_name: str | None = None
    permissions: list[str] = []
    global_permissions: list[str] = []
    effective_roles: list[str] = []
    base_role: str | None = None
    effective_role_scopes: list[dict[str, object]] = []
    mfa_enrollment_required: bool = False
    must_change_password: bool = False
    password_expired: bool = False
    password_expires_soon: bool = False
    password_changed_at: datetime | None = None


class SessionInfo(BaseModel):
    """A single active session."""

    id: UUID
    device: str | None = None
    browser: str | None = None
    location: str | None = None
    ip_address: str | None = None
    last_active_at: datetime | None = None
    expires_at: datetime
    is_current: bool
    created_at: datetime | None = None


class TokenResponse(BaseModel):
    """JWT token response after successful login."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int = 1800  # 30 minutes in seconds
    user: UserInfo


class TwoFactorChallengeResponse(BaseModel):
    """Login response when 2FA is required."""

    require_2fa: bool = True
    mfa_token: str
    expires_in: int = 300  # seconds
    message: str = "Two-factor authentication is required."


LoginResponse = TokenResponse | TwoFactorChallengeResponse


class TwoFactorSetupResponse(BaseModel):
    """POST /auth/2fa/setup — values needed to enrol an authenticator app."""

    secret: str
    otpauth_uri: str
    qr_svg: str
    account: str
    issuer: str


class TwoFactorConfirmResponse(BaseModel):
    """POST /auth/2fa/confirm — 2FA enabled + recovery codes."""

    two_factor_enabled: bool = True
    recovery_codes: list[str]


class TwoFactorRegenerateResponse(BaseModel):
    """POST /auth/2fa/regenerate — fresh recovery codes."""

    recovery_codes: list[str]


class RefreshTokenResponse(BaseModel):
    """New access token and, when rotation is enabled, refresh token."""

    access_token: str
    refresh_token: str | None = None
    token_type: str = "bearer"


class MessageResponse(BaseModel):
    """Simple acknowledgement payload."""

    message: str


class SessionListResponse(BaseModel):
    """GET /auth/sessions response."""

    sessions: list[SessionInfo]


class TwoFactorResponse(BaseModel):
    """GET /auth/2fa response."""

    two_factor_enabled: bool
    pending_setup: bool = False
    pending_expires_at: datetime | None = None


class LogoutAllResponse(BaseModel):
    """POST /auth/logout-all response."""

    revoked: int
    message: str


# Rebuild the union model
TwoFactorChallengeResponse.model_rebuild()


__all__ = [
    "LoginRequest",
    "DemoLoginRequest",
    "RefreshTokenRequest",
    "ChangePasswordRequest",
    "ForgotPasswordRequest",
    "ResetPasswordRequest",
    "LogoutRequest",
    "TwoFactorConfirmRequest",
    "TwoFactorDisableRequest",
    "TwoFactorRegenerateRequest",
    "TwoFactorVerifyRequest",
    "UserInfo",
    "SessionInfo",
    "TokenResponse",
    "TwoFactorChallengeResponse",
    "LoginResponse",
    "TwoFactorSetupResponse",
    "TwoFactorConfirmResponse",
    "TwoFactorRegenerateResponse",
    "RefreshTokenResponse",
    "MessageResponse",
    "SessionListResponse",
    "TwoFactorResponse",
    "LogoutAllResponse",
]
