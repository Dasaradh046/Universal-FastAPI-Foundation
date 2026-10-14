"""
CSRF protection utilities using double-submit tokens.
"""

from __future__ import annotations

import secrets
from fastapi import Request, Response

from app.core.logging import get_logger

logger = get_logger(__name__)

CSRF_COOKIE_NAME = "ph_csrf_token"


def generate_csrf_token() -> str:
    """Generate a new cryptographically secure CSRF token."""
    return secrets.token_urlsafe(32)


def _set_csrf_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        CSRF_COOKIE_NAME,
        token,
        httponly=False,  # Must be readable by JS for double-submit
        secure=True,
        samesite="lax",
        path="/",
    )


async def csrf_token_endpoint(request: Request) -> Response:
    """Issue a CSRF token as a cookie for double-submit pattern.

    Used by cookie-authenticated writes to prevent CSRF attacks.
    """
    from fastapi.responses import JSONResponse

    token = generate_csrf_token()
    response = JSONResponse(content={"csrf_token": token})
    _set_csrf_cookie(response, token)
    return response


__all__ = ["generate_csrf_token", "csrf_token_endpoint", "CSRF_COOKIE_NAME"]
