"""
Auth API v1 routes — login, refresh, logout, me, password management, MFA.

All routes share ``/api/v1/auth`` as their prefix (set in router.py).
"""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import (
    APIRouter,
    Body,
    Depends,
    Header,
    HTTPException,
    Request,
    Response,
    status,
)
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.dependencies import (
    CurrentUser,
    get_current_active_user,
    require_permission,
    require_super_admin,
)
from app.core.exceptions import AuthenticationError, ConflictError, NotFoundError
from app.core.logging import get_logger
from app.modules.auth.services import AuthService, get_auth_service
from app.modules.auth.schemas import (
    ChangePasswordRequest,
    DemoLoginRequest,
    ForgotPasswordRequest,
    LoginRequest,
    LogoutRequest,
    RefreshTokenRequest,
    ResetPasswordRequest,
    SessionListResponse,
    TokenResponse,
    TwoFactorChallengeResponse,
    TwoFactorConfirmRequest,
    TwoFactorDisableRequest,
    TwoFactorRegenerateRequest,
    TwoFactorResponse,
    TwoFactorSetupResponse,
    TwoFactorVerifyRequest,
    UserInfo,
)

logger = get_logger(__name__)

router = APIRouter()


def _client_ip(request: Request) -> str | None:
    """Best-effort client IP extraction (respects X-Forwarded-For when behind a proxy)."""
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else None


def _user_agent(request: Request) -> str | None:
    return request.headers.get("user-agent")


# ---- Helpers -------------------------------------------------------------- #


def _set_auth_cookies(
    response: Response,
    access_token: str,
    refresh_token: str | None = None,
) -> None:
    """Attach JWT cookies with hardened attributes."""
    response.set_cookie(
        settings.COOKIE_ACCESS_NAME,
        access_token,
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        httponly=True,
        samesite=settings.COOKIE_SAMESITE,
        secure=settings.is_prod or settings.is_staging,
        path="/",
    )
    if refresh_token:
        response.set_cookie(
            settings.COOKIE_REFRESH_NAME,
            refresh_token,
            max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 3600,
            httponly=True,
            samesite=settings.COOKIE_SAMESITE,
            secure=settings.is_prod or settings.is_staging,
            path="/auth",
        )


def _clear_auth_cookies(response: Response) -> None:
    for name in (settings.COOKIE_ACCESS_NAME, settings.COOKIE_REFRESH_NAME):
        response.delete_cookie(name, path="/", httponly=True)


# ---- Endpoints ------------------------------------------------------------ #


@router.post("/login", response_model=TokenResponse, status_code=200)
async def login(
    request: Request,
    response: Response,
    body: LoginRequest,
    session: Annotated[AsyncSession, Depends(get_db)],
    auth: Annotated[AuthService, Depends(get_auth_service)],
):
    """Sign in with email and password.

    If the account has 2FA enabled, returns a 401 with ``require_2fa=True``
    and an MFA challenge token instead of access/refresh tokens.
    """
    ip_address = _client_ip(request)
    user_agent = _user_agent(request)
    device_fingerprint = body.device_fingerprint

    result = await auth.login(
        session, body.email, body.password, ip_address, user_agent, device_fingerprint
    )

    if isinstance(result, TwoFactorChallengeResponse):
        response.status_code = status.HTTP_401_UNAUTHORIZED
        return result

    _set_auth_cookies(response, result.access_token, result.refresh_token)
    return result


@router.post("/refresh", response_model=dict, dependencies=[])
async def refresh(
    request: Request,
    response: Response,
    body: RefreshTokenRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    auth: Annotated[AuthService, Depends(get_auth_service)],
):
    """Exchange a refresh token for a new access token (with rotation)."""
    refresh_token = body.refresh_token

    if not refresh_token:
        cookie_name = settings.COOKIE_REFRESH_NAME
        refresh_token = request.cookies.get(cookie_name)

    if not refresh_token:
        raise AuthenticationError("Refresh token is required")

    tokens = await auth.refresh(db, refresh_token)
    _set_auth_cookies(response, tokens["access_token"], tokens.get("refresh_token"))
    return tokens


@router.post(
    "/refresh-cookies",
    response_model=dict,
    response_model_exclude_unset=True,
    dependencies=[],
)
async def refresh_cookies(
    request: Request,
    response: Response,
    db: Annotated[AsyncSession, Depends(get_db)],
    auth: Annotated[AuthService, Depends(get_auth_service)],
):
    """Cookie-based token refresh (reads refresh token from cookie).

    The refresh token cookie is set with a short idle lifetime and rotated on
    each use. If rotation is disabled this endpoint is equivalent to the body
    endpoint but reads the token solely from the cookie.
    """
    refresh_token = request.cookies.get(settings.COOKIE_REFRESH_NAME)
    if not refresh_token:
        raise AuthenticationError("Refresh token cookie not found")

    tokens = await auth.refresh(db, refresh_token)
    _set_auth_cookies(response, tokens["access_token"], tokens.get("refresh_token"))
    return tokens


@router.post("/logout", response_model=dict)
async def logout(
    request: Request,
    response: Response,
    body: LogoutRequest,
    session: Annotated[AsyncSession, Depends(get_db)],
    auth: Annotated[AuthService, Depends(get_auth_service)],
):
    """Revoke the presented access + refresh tokens and clear cookies."""
    access_token = _extract_token(request)
    refresh_token = body.refresh_token or request.cookies.get(settings.COOKIE_REFRESH_NAME)

    await auth.logout(session, access_token, refresh_token)
    _clear_auth_cookies(response)
    return {"message": "Logged out successfully"}


@router.post("/logout-all", response_model=dict, status_code=200)
async def logout_all(
    request: Request,
    response: Response,
    session: Annotated[AsyncSession, Depends(get_db)],
    auth: Annotated[AuthService, Depends(get_auth_service)],
):
    """Sign the current user out of every device."""
    access_token = _extract_token(request)
    refresh_token = request.cookies.get(settings.COOKIE_REFRESH_NAME)

    if not access_token and not refresh_token:
        raise AuthenticationError("No active session to revoke")

    result = await auth.logout_all(session, access_token, refresh_token)
    _clear_auth_cookies(response)
    return result


@router.get("/me", response_model=UserInfo)
async def me(
    user: Annotated[CurrentUser, Depends(get_current_active_user)],
    session: Annotated[AsyncSession, Depends(get_db)],
    auth: Annotated[AuthService, Depends(get_auth_service)],
):
    """Return the current user's profile and effective permissions."""
    return await auth.get_me(session, user)


@router.get("/sessions", response_model=SessionListResponse)
async def list_sessions(
    user: Annotated[CurrentUser, Depends(get_current_active_user)],
    session: Annotated[AsyncSession, Depends(get_db)],
    auth: Annotated[AuthService, Depends(get_auth_service)],
):
    """List all active device sessions for the current user."""
    sessions = await auth.list_sessions(session, user)
    return SessionListResponse(sessions=sessions)


@router.delete(
    "/sessions/{session_id}",
    response_model=dict,
    dependencies=[Depends(get_current_active_user)],
)
async def revoke_session(
    session_id: UUID,
    user: Annotated[CurrentUser, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    auth: Annotated[AuthService, Depends(get_auth_service)],
):
    """Revoke a specific device session (other than the current one)."""
    return await auth.revoke_device_session(db, user, session_id)


@router.delete(
    "/sessions",
    response_model=dict,
    dependencies=[Depends(get_current_active_user)],
)
async def revoke_other_sessions(
    keep_current: bool = True,
    user: Annotated[CurrentUser, Depends(get_current_active_user)] = ...,
    db: Annotated[AsyncSession, Depends(get_db)] = ...,
    auth_svc: Annotated[AuthService, Depends(get_auth_service)] = ...,
):
    """Revoke all device sessions except the current one."""
    keep_id = user.session_id if keep_current else None
    return await auth_svc.revoke_other_device_sessions(db, user, keep_session_id=keep_id)


@router.get("/2fa", response_model=TwoFactorResponse)
async def two_factor_status(
    user: Annotated[CurrentUser, Depends(get_current_active_user)],
    session: Annotated[AsyncSession, Depends(get_db)],
    auth: Annotated[AuthService, Depends(get_auth_service)],
):
    """Return the current user's 2FA status and any pending setup."""
    return await auth.get_two_factor_status(session, user)


@router.post("/2fa/setup", response_model=TwoFactorSetupResponse)
async def setup_two_factor(
    user: Annotated[CurrentUser, Depends(get_current_active_user)],
    session: Annotated[AsyncSession, Depends(get_db)],
    auth: Annotated[AuthService, Depends(get_auth_service)],
):
    """Begin 2FA enrollment — returns the TOTP secret and QR code."""
    return await auth.setup_two_factor(session, user)


@router.post("/2fa/confirm", response_model=TwoFactorSetupResponse)
async def confirm_two_factor(
    user: Annotated[CurrentUser, Depends(get_current_active_user)],
    body: TwoFactorConfirmRequest,
    session: Annotated[AsyncSession, Depends(get_db)],
    auth: Annotated[AuthService, Depends(get_auth_service)],
):
    """Verify the TOTP code from the authenticator app to complete 2FA setup."""
    result = await auth.confirm_two_factor(session, user, body.token)
    return result


@router.post("/2fa/disable", response_model=dict)
async def disable_two_factor(
    user: Annotated[CurrentUser, Depends(get_current_active_user)],
    body: TwoFactorDisableRequest,
    session: Annotated[AsyncSession, Depends(get_db)],
    auth: Annotated[AuthService, Depends(get_auth_service)],
):
    """Disable 2FA — requires a valid TOTP or recovery code."""
    return await auth.disable_two_factor(session, user, body.token)


@router.post("/2fa/regenerate", response_model=dict)
async def regenerate_recovery_codes(
    user: Annotated[CurrentUser, Depends(get_current_active_user)],
    body: TwoFactorRegenerateRequest,
    session: Annotated[AsyncSession, Depends(get_db)],
    auth: Annotated[AuthService, Depends(get_auth_service)],
):
    """Issue a fresh set of recovery codes (old ones are revoked)."""
    result = await auth.regenerate_recovery_codes(session, user, body.token)
    return result


@router.post("/2fa/verify", response_model=TokenResponse)
async def verify_two_factor(
    request: Request,
    response: Response,
    body: TwoFactorVerifyRequest,
    session: Annotated[AsyncSession, Depends(get_db)],
    auth: Annotated[AuthService, Depends(get_auth_service)],
):
    """Complete a login that required 2FA.

    Takes the MFA challenge token (from ``POST /auth/login``) and the TOTP
    code or recovery code. On success, issues access + refresh tokens.
    """
    ip_address = _client_ip(request)
    user_agent = _user_agent(request)
    result = await auth.complete_mfa_login(
        session,
        body.mfa_token,
        body.token,
        ip_address,
        user_agent,
        body.device_fingerprint,
    )
    _set_auth_cookies(response, result.access_token, result.refresh_token)
    return result


# ---- Password management ---------------------------------------------------- #


@router.post("/change-password", response_model=dict)
async def change_password(
    user: Annotated[CurrentUser, Depends(get_current_active_user)],
    body: ChangePasswordRequest,
    session: Annotated[AsyncSession, Depends(get_db)],
    auth: Annotated[AuthService, Depends(get_auth_service)],
):
    """Change the current user's password (all sessions are revoked)."""
    return await auth.change_password(session, user, body.current_password, body.new_password)


@router.post("/forgot-password", response_model=dict, status_code=200)
async def forgot_password(
    request: Request,
    body: ForgotPasswordRequest,
    session: Annotated[AsyncSession, Depends(get_db)],
    auth: Annotated[AuthService, Depends(get_auth_service)],
):
    """Request a password-reset link via email."""
    ip_address = _client_ip(request)
    return await auth.request_password_reset(session, body.email, ip_address)


@router.post("/reset-password", response_model=dict)
async def reset_password(
    request: Request,
    body: ResetPasswordRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    auth: Annotated[AuthService, Depends(get_auth_service)],
):
    """Consume a reset token and set a new password."""
    ip_address = _client_ip(request)
    return await auth.reset_password(db, body.token, body.new_password, ip_address)


# ---- Demo login (local/dev only) ------------------------------------------- #


@router.post("/login/demo", response_model=TokenResponse, status_code=200)
async def demo_login(
    request: Request,
    response: Response,
    body: DemoLoginRequest,
    session: Annotated[AsyncSession, Depends(get_db)],
    auth: Annotated[AuthService, Depends(get_auth_service)],
):
    """Sign in as a demo persona (local/development environments only)."""
    if settings.ENVIRONMENT not in {"local", "development"}:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Demo login is not available.",
        )
    ip_address = _client_ip(request)
    user_agent = _user_agent(request)
    result = await auth.demo_login(
        session, body.persona, ip_address, user_agent, body.device_fingerprint
    )
    _set_auth_cookies(response, result.access_token, result.refresh_token)
    return result


# ---- Internal helpers ------------------------------------------------------ #


def _extract_token(request: Request) -> str | None:
    """Extract bearer token from Authorization header or cookie."""
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        return auth_header[len("Bearer ") :].strip()
    return request.cookies.get(settings.COOKIE_ACCESS_NAME)
