"""
Security utilities — JWT tokens + password hashing.

JWT design (hardened)
---------------------
- **Algorithms**: HS256/HS384/HS512 (symmetric, dev/small deployments) or
  **RS256** (asymmetric RSA — recommended for production). With RS256 only
  the private key can sign; verifiers (other services, JWKS consumers) need
  only the public key, so a leaked verification key cannot forge tokens.
- **Algorithm-confusion protection**: verification pins the exact expected
  algorithm — the allowed ``algorithms`` list never mixes families, so an
  attacker cannot downgrade an RS256 token to ``alg: none`` or HS256.
- **Claim validation**: ``exp``, ``nbf``/``iat`` (with configurable leeway),
  ``iss`` (issuer) and ``aud`` (audience) are verified on every decode.
- **Token identity**: every token carries a unique ``jti`` (for logging and
  future revocation lists) and a ``type`` claim so a refresh token can never
  be used as an access token.
- **Password hashing**: bcrypt with a per-hash random salt.
"""

from __future__ import annotations

import os
import uuid
import secrets
from datetime import UTC, datetime, timedelta
from functools import lru_cache
from pathlib import Path
from typing import Any
from uuid import UUID

import bcrypt
from jose import JWTError, jwt

from app.core.config import settings
from app.core.logging import get_logger
from app.core.exceptions import AppException

logger = get_logger(__name__)

# ---- Key loading (RS256) ----------------------------------------------- #


def _uses_rs256() -> bool:
    """True when the configured signing algorithm is RS256."""
    return settings.JWT_ALGORITHM == "RS256"


def _effective_algorithm() -> str:
    """Resolve the algorithm actually used to sign/verify tokens.

    RS256 wins when key material is present; otherwise the configured HS*
    algorithm is used. Misconfiguration (RS256 requested but keys missing)
    raises instead of silently degrading.
    """
    if settings.JWT_ALGORITHM == "RS256":
        if settings.JWT_PRIVATE_KEY_PATH and settings.JWT_PUBLIC_KEY_PATH:
            return "RS256"
        raise AppException(
            status_code=500,
            detail="JWT_ALGORITHM=RS256 but JWT_PRIVATE_KEY_PATH/JWT_PUBLIC_KEY_PATH are not configured. "
                   "Run: python scripts/generate_keys.py"
        )
    return settings.JWT_ALGORITHM


@lru_cache(maxsize=4)
def _load_pem(path: str, is_private: bool) -> bytes:
    """Load a PEM file, warning on loose private-key file permissions.

    The POSIX permission-bit check only runs on POSIX systems. On Windows,
    ``stat().st_mode`` is synthetic — ``0o666`` merely means "writable" and
    ``0o444`` "read-only" — so it never reflects actual NTFS ACLs and the
    check would fire on every load. Windows key files are ACL-restricted to
    the current user by ``scripts/generate_keys.py`` (``icacls``).
    """
    p = Path(path)
    if not p.is_file():
        raise AppException(
            status_code=500,
            detail=f"JWT key file not found: {path!r}"
        )
    if is_private and os.name == "posix":
        mode = p.stat().st_mode & 0o777
        if mode & 0o077:
            logger.warning(
                "Private key %s is group/other-readable (mode %o) — restrict it with chmod 600.",
                path,
                mode,
            )
    return p.read_bytes()


def _signing_key() -> str | bytes:
    if _uses_rs256():
        return _load_pem(settings.JWT_PRIVATE_KEY_PATH, is_private=True)
    return settings.SECRET_KEY


def _verification_key() -> str | bytes:
    if _uses_rs256():
        return _load_pem(settings.JWT_PUBLIC_KEY_PATH, is_private=False)
    return settings.SECRET_KEY


def _token_headers() -> dict[str, str]:
    return {"typ": "JWT"}


# ---- Password hashing -------------------------------------------------- #


def hash_password(plain: str) -> str:
    """Hash a plaintext password using bcrypt."""
    if not plain or len(plain.strip()) == 0:
        raise ValueError("Password cannot be empty")
    
    pw = plain.encode("utf-8")
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(pw, salt).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    """Verify a plaintext password against a bcrypt hash."""
    if not plain or not hashed:
        return False
    
    try:
        return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))
    except Exception:
        return False


# ---- JWT tokens -------------------------------------------------------- #


def create_access_token(
    subject: str | uuid.UUID,
    tenant_id: str | uuid.UUID,
    role: str,
    extra_claims: dict[str, Any] | None = None,
) -> str:
    """Create a short-lived JWT access token (verified strictly on decode)."""
    return _create_token(
        token_type="access",
        subject=subject,
        tenant_id=tenant_id,
        role=role,
        lifetime=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
        extra_claims=extra_claims,
    )


def create_refresh_token(
    subject: str | uuid.UUID,
    tenant_id: str | uuid.UUID,
    expires_at: datetime | None = None,
) -> str:
    """Create a long-lived JWT refresh token (no role claim — re-issued on use).

    ``expires_at`` caps the token's ``exp`` (used by refresh-token rotation to
    keep a rotated token from outliving its session under the fixed-lifetime
    policy). When omitted the token lives ``REFRESH_TOKEN_EXPIRE_DAYS``.
    """
    if expires_at is not None:
        lifetime = expires_at - datetime.now(UTC)
        if lifetime <= timedelta(0):
            lifetime = timedelta(seconds=1)
    else:
        lifetime = timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    return _create_token(
        token_type="refresh",
        subject=subject,
        tenant_id=tenant_id,
        role="",
        lifetime=lifetime,
    )


def create_mfa_token(
    subject: str | uuid.UUID,
    tenant_id: str | uuid.UUID,
    role: str,
    lifetime_minutes: int = 5,
) -> str:
    """Create a short-lived, single-use MFA step-up token.

    Issued after a successful *password* login when the account has 2FA
    enabled. It proves the password step only — the caller must then present
    a valid TOTP/recovery code before ``access``/``refresh`` tokens are
    minted. The ``jti`` is blacklisted on successful redemption.
    """
    return _create_token(
        token_type="mfa",
        subject=subject,
        tenant_id=tenant_id,
        role=role,
        lifetime=timedelta(minutes=lifetime_minutes),
    )


def _create_token(
    *,
    token_type: str,
    subject: str | uuid.UUID,
    tenant_id: str | uuid.UUID,
    role: str,
    lifetime: timedelta,
    extra_claims: dict[str, Any] | None = None,
) -> str:
    now = datetime.now(UTC)
    payload: dict[str, Any] = {
        # Registered claims
        "sub": str(subject),
        "iss": settings.JWT_ISSUER,
        "aud": settings.JWT_AUDIENCE,
        "iat": int(now.timestamp()),
        "nbf": int(now.timestamp()),
        "exp": int((now + lifetime).timestamp()),
        "jti": uuid.uuid4().hex,
        # Application claims
        "type": token_type,
        "tenant_id": str(tenant_id),
        "role": role,
    }
    if extra_claims:
        payload.update(extra_claims)
    return jwt.encode(
        payload,
        _signing_key(),
        algorithm=_effective_algorithm(),
        headers=_token_headers(),
    )


def decode_token(token: str) -> dict[str, Any] | None:
    """Decode and verify a JWT token. Returns the payload, or None.

    Verifies signature (pinned algorithm), expiry (with leeway), issuer and
    audience. Returns None — never raises — so callers keep their existing
    ``if not payload`` handling.
    """
    if not token or not isinstance(token, str):
        return None
        
    algorithm = _effective_algorithm()
    try:
        # Pin the algorithm: exactly the configured algorithm, never a list
        # that mixes families (prevents alg-downgrade/none attacks).
        payload = jwt.decode(
            token,
            _verification_key(),
            algorithms=[algorithm],
            issuer=settings.JWT_ISSUER,
            audience=settings.JWT_AUDIENCE,
            options={
                # python-jose reads leeway (seconds) from options.
                "leeway": settings.JWT_LEEWAY_SECONDS,
                "require": ["exp", "iat", "sub", "type"],
            },
        )
        return payload
    except JWTError as exc:
        logger.info("JWT rejected (%s): %s", algorithm, exc.__class__.__name__)
        return None
    except Exception as exc:
        logger.error(f"Unexpected error during JWT decoding: {exc}")
        return None


# ---- Token blacklist (in-memory, replace with Redis in production) ---- #


_TOKEN_REVOCATIONS: dict[str, int] = {}  # jti -> expiry timestamp


def revoke_token(jti: str, exp: int) -> None:
    """Add a token's jti to the blacklist until its natural expiry."""
    if not jti or not isinstance(jti, str):
        return
        
    _TOKEN_REVOCATIONS[jti] = exp


def is_token_revoked(jti: str) -> bool:
    """Check if a token's jti is blacklisted and not yet expired."""
    if not jti or not isinstance(jti, str):
        return False
        
    exp = _TOKEN_REVOCATIONS.get(jti)
    if exp is None:
        return False
    if int(datetime.now(UTC).timestamp()) > exp:
        # Expired revocation entry — clean it up
        _TOKEN_REVOCATIONS.pop(jti, None)
        return False
    return True


def revoke_all_for_user(user_id: str) -> None:
    """Best-effort sweep: blacklist all outstanding tokens for a user.

    In a production deployment this would query Redis for keys matching
    ``user:{user_id}:*`` and delete them. Here it is a no-op placeholder.
    """
    # Placeholder for production Redis-based implementation
    # In production, this would scan Redis for keys matching the pattern
    pass


# ---- Refresh token hashing --------------------------------------------- #


def _hash_refresh_token(token: str) -> str:
    """SHA-256 hash of a refresh token (stored in UserSession row)."""
    import hashlib

    return hashlib.sha256(token.encode()).hexdigest()


# ---- MFA / 2FA utilities ----------------------------------------------- #


def generate_totp_secret() -> str:
    """Generate a base32 TOTP secret."""
    import base64

    return base64.b32encode(secrets.token_bytes(20)).decode().rstrip("=")


def verify_totp(secret: str, token: str, window: int = 1) -> bool:
    """Verify a TOTP code against a secret.

    ``window`` allows ±1 time step (30s each) for clock drift.
    """
    import pyotp

    if not secret or not token:
        return False
        
    try:
        totp = pyotp.TOTP(secret)
        return totp.verify(token, valid_window=window)
    except Exception:
        return False


def otpauth_uri(secret: str, account: str, issuer: str) -> str:
    """Build an ``otpauth://`` URI for QR code generation."""
    import urllib.parse

    if not secret or not account or not issuer:
        raise ValueError("Secret, account, and issuer are required")
        
    return (
        f"otpauth://totp/{urllib.parse.quote(issuer)}:"
        f"{urllib.parse.quote(account)}?secret={secret}&issuer={urllib.parse.quote(issuer)}"
    )


def _render_qr_svg(uri: str) -> str:
    """Render the otpauth URI as an inline SVG QR code."""
    import qrcode
    from io import BytesIO

    if not uri:
        raise ValueError("URI is required")
        
    qr = qrcode.QRCode(box_size=10, border=4)
    qr.add_data(uri)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buf = BytesIO()
    img.save(buf, format="SVG")
    return buf.getvalue().decode()


def generate_recovery_codes(count: int = 10, length: int = 10) -> list[str]:
    """Generate a list of one-time recovery codes (alphanumeric)."""
    import string

    if count <= 0:
        return []
        
    alphabet = string.ascii_uppercase + string.digits
    return [
        "".join(secrets.choice(alphabet) for _ in range(length))
        for _ in range(count)
    ]


def hash_recovery_codes(codes: list[str]) -> str:
    """SHA-256 hash each recovery code; return newline-joined hashes."""
    import hashlib

    if not codes:
        return ""
        
    return "\n".join(hashlib.sha256(c.encode()).hexdigest() for c in codes)


def redeem_recovery_code(stored_hashes: str, token: str) -> str | None:
    """Verify a recovery code against stored hashes.

    On success, returns the *remaining* hashes as a newline-joined string
    (the used code is removed). On failure returns ``None``.
    """
    import hashlib

    if not stored_hashes or not token:
        return None
        
    try:
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        lines = stored_hashes.splitlines()
        for i, h in enumerate(lines):
            if h == token_hash:
                # Remove this one and return the rest
                lines.pop(i)
                return "\n".join(lines)
        return None
    except Exception:
        return None


# ---- Password policy --------------------------------------------------- #


class PasswordStrength:
    """Result of a password strength check."""

    def __init__(self, is_strong: bool, score: int, suggestions: list[str]):
        self.is_strong = is_strong
        self.score = score
        self.suggestions = suggestions


def check_password_strength(password: str) -> PasswordStrength:
    """Validate a password against the configured policy.

    Returns a :class:`PasswordStrength` object with a boolean ``is_strong``,
    a numeric ``score`` (0-4) and a list of human-readable suggestions.
    """
    if not password:
        return PasswordStrength(
            is_strong=False,
            score=0,
            suggestions=["Password cannot be empty"]
        )
        
    score = 0
    suggestions: list[str] = []

    if len(password) >= settings.PASSWORD_MIN_LENGTH:
        score += 1
    else:
        suggestions.append(
            f"Must be at least {settings.PASSWORD_MIN_LENGTH} characters."
        )

    if any(c.islower() for c in password):
        score += 1
    else:
        suggestions.append("Must contain at least one lowercase letter.")

    if any(c.isupper() for c in password):
        score += 1
    else:
        suggestions.append("Must contain at least one uppercase letter.")

    if any(c.isdigit() for c in password):
        score += 1
    else:
        suggestions.append("Must contain at least one digit.")

    if any(not c.isalnum() for c in password):
        score += 1
    else:
        suggestions.append("Must contain at least one special character.")

    # Optional: blocklist check
    if settings.PASSWORD_BLOCKLIST_ENABLED and password in settings.PASSWORD_BLOCKLIST:
        score = 0
        suggestions.append("This password is on the blocklist.")

    return PasswordStrength(is_strong=score >= 4, score=score, suggestions=suggestions)


def generate_temporary_password(length: int = 16) -> str:
    """Generate a strong temporary password for admin issuance."""
    import string

    if length < 8:
        length = 16  # Minimum secure length
        
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
    while True:
        pwd = "".join(secrets.choice(alphabet) for _ in range(length))
        if check_password_strength(pwd).is_strong:
            return pwd


# CurrentUser class for authentication context
from dataclasses import dataclass, field
from typing import List, Annotated
from fastapi import Depends, HTTPException, Request, status
from app.core.enums import Role
from app.core.security import decode_token, is_token_revoked
from app.core.permissions import (
    ROLE_PERMISSIONS, 
    get_permissions_for_role,
    has_permission,
    has_any_permission,
    get_role_from_token,
    get_user_id_from_token,
    get_tenant_id_from_token,
)
from app.core.role_aliases import normalize_role

# Token retrieval helper ------------------------------------------------------ #


def _extract_token(request: Request) -> str | None:
    """Pull a bearer token from the Authorization header or a cookie."""
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        return auth_header[len("Bearer ") :].strip()

    cookie_name = settings.COOKIE_ACCESS_NAME
    cookie_token = request.cookies.get(cookie_name)
    if cookie_token:
        return cookie_token
    return None


# AuthContext ---------------------------------------------------------------- #


@dataclass
class CurrentUser:
    """Authenticated principal extracted from a validated access token."""

    id: UUID
    email: str
    role: str
    tenant_id: UUID
    session_id: UUID | None = None
    permissions: list[str] = field(default_factory=list)
    effective_roles: list[str] = field(default_factory=list)
    is_super_admin: bool = False
    is_platform_admin: bool = False
    mfa_enrollment_required: bool = False
    must_change_password: bool = False

    def has_permission(self, permission: str) -> bool:
        """True if this user has ``permission``.

        The wildcard ``"*"`` grants everything; ``"*.own"`` grants any own-scope
        action on any resource (used for self-service profile edits).
        """
        return has_permission(self.permissions, permission)

    def has_any_permission(self, *perms: str) -> bool:
        """True if this user has any of the given permissions."""
        return has_any_permission(self.permissions, *perms)

    def has_role(self, *role_names: str) -> bool:
        """True if the user holds any of the given roles (alias-normalized)."""
        if self.is_super_admin:
            return True
        normalized = {normalize_role(r) for r in role_names}
        return bool(normalized.intersection(set(self.effective_roles)))

    def has_any_role(self, *role_names: str) -> bool:
        """True if the user holds any of the given roles."""
        return self.has_role(*role_names)


def _token_to_current_user(payload: dict[str, Any]) -> CurrentUser:
    """Build a :class:`CurrentUser` from a decoded JWT payload."""
    try:
        permissions: list[str] = payload.get("permissions", [])
        roles: list[str] = payload.get("roles", []) or [payload.get("role", "")]
        sid = payload.get("sid")
        session_id = UUID(sid) if sid else None

        role = payload.get("role", "")
        normalized_role = normalize_role(role)
        is_super_admin = normalized_role == Role.PLATFORM_OWNER.value
        is_platform_admin = normalized_role in {
            Role.PLATFORM_ADMIN.value,
            Role.PLATFORM_OWNER.value,
        }

        # If the token already carries permissions, use them; otherwise derive from roles.
        if not permissions:
            permissions = get_permissions_for_role(normalized_role)
            # If we have multiple roles, compute union of permissions
            if len(roles) > 1:
                all_permissions = set()
                for role in roles:
                    normalized_role = normalize_role(role)
                    all_permissions.update(get_permissions_for_role(normalized_role))
                permissions = list(all_permissions)

        return CurrentUser(
            id=UUID(payload["sub"]),
            email=payload.get("email", ""),
            role=role,
            tenant_id=UUID(payload["tenant_id"]),
            session_id=session_id,
            permissions=permissions,
            effective_roles=roles,
            is_super_admin=is_super_admin,
            is_platform_admin=is_platform_admin,
            mfa_enrollment_required=bool(payload.get("mfa_enrollment_required", False)),
            must_change_password=bool(payload.get("must_change_password", False)),
        )
    except (KeyError, ValueError, TypeError) as exc:
        raise AuthenticationError("Invalid or expired token") from exc


async def get_current_user(request: Request) -> CurrentUser:
    """Resolve the authenticated user from the request's bearer token."""
    token = _extract_token(request)
    if not token:
        raise AuthenticationError("Not authenticated — missing token")

    payload = decode_token(token)
    if not payload:
        raise AuthenticationError("Invalid or expired token")

    if payload.get("type") != "access":
        raise AuthenticationError("Expected an access token")

    jti = payload.get("jti")
    if jti and is_token_revoked(jti):
        raise AuthenticationError("Session has been revoked — please sign in again")

    try:
        return _token_to_current_user(payload)
    except AuthenticationError:
        raise
    except Exception as exc:
        raise AuthenticationError("Invalid or expired token") from exc


async def get_current_active_user(
    user: Annotated[CurrentUser, Depends(get_current_user)],
) -> CurrentUser:
    """Shortcut that additionally verifies the account is active."""
    # In a real implementation, this would check if the user is active in the database
    # For now, we just return the user as-is
    return user


def require_permission(*permissions: str):
    """Dependency factory: require one-or-more of the given permissions.

    A user with the ``"*"`` wildcard (platform_owner) auto-passes.
    """

    def _checker(user: Annotated[CurrentUser, Depends(get_current_user)]) -> CurrentUser:
        for perm in permissions:
            if user.has_permission(perm):
                return user
        raise PermissionError(
            f"Insufficient permissions — requires one of: {', '.join(permissions)}"
        )

    return _checker


def require_role(*allowed_roles: str):
    """Dependency factory: require one of the given roles."""

    def _checker(user: Annotated[CurrentUser, Depends(get_current_user)]) -> CurrentUser:
        if user.has_role(*allowed_roles):
            return user
        raise PermissionError(
            f"Requires role: {', '.join(allowed_roles)} (current: {user.role})"
        )

    return _checker


def require_super_admin(
    user: Annotated[CurrentUser, Depends(get_current_user)],
) -> CurrentUser:
    """Dependency: require a platform_owner or is_super_admin flag."""
    if not user.is_super_admin:
        raise PermissionError("Platform owner privileges required")
    return user


def require_platform_admin(
    user: Annotated[CurrentUser, Depends(get_current_user)],
) -> CurrentUser:
    """Dependency: require a platform_admin or above."""
    if not user.is_platform_admin:
        raise PermissionError("Platform admin privileges required")
    return user


def require_tenant_admin(
    user: Annotated[CurrentUser, Depends(get_current_user)],
) -> CurrentUser:
    """Dependency: require a tenant_admin role or above."""
    if user.is_super_admin or user.is_platform_admin:
        return user
    if user.has_role(Role.TENANT_ADMIN.value):
        return user
    raise PermissionError("Tenant admin privileges required")


__all__ = [
    "hash_password",
    "verify_password",
    "create_access_token",
    "create_refresh_token",
    "create_mfa_token",
    "decode_token",
    "revoke_token",
    "is_token_revoked",
    "revoke_all_for_user",
    "_hash_refresh_token",
    "generate_totp_secret",
    "verify_totp",
    "otpauth_uri",
    "_render_qr_svg",
    "generate_recovery_codes",
    "hash_recovery_codes",
    "redeem_recovery_code",
    "check_password_strength",
    "generate_temporary_password",
    "PasswordStrength",
    "CurrentUser",
    "get_current_user",
    "get_current_active_user",
    "require_permission",
    "require_role",
    "require_super_admin",
    "require_platform_admin",
    "require_tenant_admin",
]