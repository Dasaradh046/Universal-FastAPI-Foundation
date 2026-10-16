"""
Exceptions package.
"""
from .exceptions import (
    AppException,
    NotFoundError,
    AuthenticationError,
    PermissionError,
    BadRequestError,
    ConflictError,
    ValidationError,
    NotFoundException,
    UnauthorizedException,
    ForbiddenException,
    app_exception_handler,
    http_exception_handler,
    general_exception_handler,
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