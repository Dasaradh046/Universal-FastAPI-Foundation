"""
Security utilities — JWT tokens + password hashing.

JWT design (hardened)
---------------------
- **Algorithms**: HS256/HS384/HS512 (symmetric, dev/small deployments) or
  **RS256** (asymmetric RSA — recommended for production). With RS256 only
  the private key can sign; verifiers (other services, JWKS consumers) need
  only the public key, so a leaked verification key cannot forge tokens.
  Configure via ``JWT_PRIVATE_KEY_PATH`` / ``JWT_PUBLIC_KEY_PATH``.
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

import bcrypt
from jose import JWTError, jwt

from app.core.config import settings
from app.core.logging import get_logger

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
        raise RuntimeError(
            "JWT_ALGORITHM=RS256 but JWT_PRIVATE_KEY_PATH/"
            "JWT_PUBLIC_KEY_PATH are not configured. Run: "
            "python scripts/generate_keys.py"
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
        raise RuntimeError(f"JWT key file not found: {path!r}")
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
    pw = plain.encode("utf-8")
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(pw, salt).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    """Verify a plaintext password against a bcrypt hash."""
    return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))


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


# ---- Token blacklist (in-memory, replace with Redis in production) ---- #

_TOKEN_REVOCATIONS: dict[str, int] = {}  # jti -> expiry timestamp


def revoke_token(jti: str, exp: int) -> None:
    """Add a token's jti to the blacklist until its natural expiry."""
    _TOKEN_REVOCATIONS[jti] = exp


def is_token_revoked(jti: str) -> bool:
    """Check if a token's jti is blacklisted and not yet expired."""
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

    totp = pyotp.TOTP(secret)
    return totp.verify(token, valid_window=window)


def otpauth_uri(secret: str, account: str, issuer: str) -> str:
    """Build an ``otpauth://`` URI for QR code generation."""
    import urllib.parse

    return (
        f"otpauth://totp/{urllib.parse.quote(issuer)}:"
        f"{urllib.parse.quote(account)}?secret={secret}&issuer={urllib.parse.quote(issuer)}"
    )


def _render_qr_svg(uri: str) -> str:
    """Render the otpauth URI as an inline SVG QR code."""
    import qrcode
    from io import BytesIO

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

    alphabet = string.ascii_uppercase + string.digits
    return [
        "".join(secrets.choice(alphabet) for _ in range(length))
        for _ in range(count)
    ]


def hash_recovery_codes(codes: list[str]) -> str:
    """SHA-256 hash each recovery code; return newline-joined hashes."""
    import hashlib

    return "\n".join(hashlib.sha256(c.encode()).hexdigest() for c in codes)


def redeem_recovery_code(stored_hashes: str, token: str) -> str | None:
    """Verify a recovery code against stored hashes.

    On success, returns the *remaining* hashes as a newline-joined string
    (the used code is removed). On failure returns ``None``.
    """
    import hashlib

    token_hash = hashlib.sha256(token.encode()).hexdigest()
    lines = stored_hashes.splitlines()
    for i, h in enumerate(lines):
        if h == token_hash:
            # Remove this one and return the rest
            lines.pop(i)
            return "\n".join(lines)
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

    alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
    while True:
        pwd = "".join(secrets.choice(alphabet) for _ in range(length))
        if check_password_strength(pwd).is_strong:
            return pwd
