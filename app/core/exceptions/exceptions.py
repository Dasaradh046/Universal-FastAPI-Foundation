"""
Custom exception classes and exception handlers.
"""

from __future__ import annotations

from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from typing import Any

from app.core.logging.logging import get_logger

logger = get_logger(__name__)


class AppException(HTTPException):
    """Base application exception."""

    def __init__(
        self,
        status_code: int,
        detail: str,
        headers: dict | None = None,
    ):
        super().__init__(status_code=status_code, detail=detail, headers=headers)
        self.status_code = status_code
        self.detail = detail
        self.headers = headers


class NotFoundError(AppException):
    """Resource not found exception (404)."""

    def __init__(self, detail: str = "Resource not found"):
        super().__init__(status_code=404, detail=detail)


class AuthenticationError(AppException):
    """Authentication failure (401)."""

    def __init__(self, detail: str = "Authentication failed", error_code: str | None = None):
        super().__init__(
            status_code=401,
            detail=detail,
            headers={"WWW-Authenticate": "Bearer"},
        )
        self.error_code = error_code


class PermissionError(AppException):
    """Permission denied (403)."""

    def __init__(self, detail: str = "Permission denied"):
        super().__init__(status_code=403, detail=detail)


class BadRequestError(AppException):
    """Bad request (400)."""

    def __init__(self, detail: str = "Bad request"):
        super().__init__(status_code=400, detail=detail)


class ConflictError(AppException):
    """Conflict (409)."""

    def __init__(self, detail: str = "Conflict"):
        super().__init__(status_code=409, detail=detail)


class ValidationError(AppException):
    """Validation error (400)."""

    def __init__(
        self,
        detail: str = "Validation failed",
        **context: Any,
    ):
        super().__init__(status_code=400, detail=detail)
        self.context = context


# ---- Backwards-compatible aliases (old names) ----

NotFoundException = NotFoundError
UnauthorizedException = AuthenticationError
ForbiddenException = PermissionError


async def app_exception_handler(request: Request, exc: Exception):
    """Handle application exceptions."""
    if not isinstance(exc, AppException):
        raise exc
    logger.error("AppException: %s", exc.detail)
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
        headers=exc.headers,
    )


async def http_exception_handler(request: Request, exc: Exception):
    """Handle HTTP exceptions."""
    if not isinstance(exc, HTTPException):
        raise exc
    logger.error("HTTPException: %s", exc.detail)
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
        headers=exc.headers,
    )


async def general_exception_handler(request: Request, exc: Exception):
    """Handle general exceptions."""
    logger.error("Unhandled exception: %s", str(exc), exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
    )


__all__ = [
    "AppException",
    "NotFoundError",
    "AuthenticationError",
    "PermissionError",
    "BadRequestError",
    "ConflictError",
    "ValidationError",
    "NotFoundException",
    "UnauthorizedException",
    "ForbiddenException",
    "app_exception_handler",
    "http_exception_handler",
    "general_exception_handler",
]
