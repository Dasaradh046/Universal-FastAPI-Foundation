"""
Rate limiting utilities.

Provides a decorator-based rate limiter and an enforcement function.
In production, this should be backed by a shared store (Redis) for
multi-instance deployments.
"""

from __future__ import annotations

import time
from collections import defaultdict
from functools import wraps
from typing import Callable

from fastapi import Request, Response
from fastapi.responses import JSONResponse

from app.core.config.settings import settings
from app.core.logging.logging import get_logger

logger = get_logger(__name__)

# In-memory rate limit store: (ip, endpoint) -> list of timestamps
_rate_limits: dict[tuple[str, str], list[float]] = defaultdict(list)


def _client_ip(request: Request) -> str:
    """Extract client IP from request."""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[-1].strip()
    return request.client.host if request.client else "unknown"


def _enforce(
    request: Request,
    key: str,
    requests: int,
    window_seconds: int,
) -> None:
    """Internal enforcement logic.

    Raises ``PermissionError`` (429) if the rate limit is exceeded.
    """
    from app.core.exceptions.exceptions import PermissionError

    ip = _client_ip(request)
    store_key = (ip, key)
    now = time.time()
    timestamps = _rate_limits[store_key]
    # Prune old entries
    timestamps[:] = [t for t in timestamps if now - t < window_seconds]
    if len(timestamps) >= requests:
        logger.warning(
            "Rate limit exceeded: ip=%s key=%s requests=%s window=%ss",
            ip, key, requests, window_seconds,
        )
        retry_after = int(window_seconds - (now - timestamps[0])) if timestamps else window_seconds
        raise PermissionError(
            f"Rate limit exceeded. Try again in {retry_after} seconds."
        )
    timestamps.append(now)


async def enforce_rate_limit(
    request: Request,
    requests: int,
    window_seconds: int,
) -> None:
    """Enforce a rate limit, raising on excess.

    Use this directly in route handlers (e.g. login endpoint) where you need
    to keep the ``response_model`` decorator.
    """
    key = f"{request.url.path}"
    _enforce(request, key, requests, window_seconds)


def rate_limit(requests: int, window_seconds: int) -> Callable:
    """Decorator for rate-limited endpoints.

    Use this on simple endpoints where you don't need ``response_model``
    serialization or need to return rate-limit headers.
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args: object, **kwargs: object) -> Response:
            request = kwargs.get("request")
            if not request:
                for arg in args:
                    if isinstance(arg, Request):
                        request = arg
                        break
            if request:
                _enforce(request, f"{request.url.path}", requests, window_seconds)
            result = await func(*args, **kwargs)
            return result

        return wrapper

    return decorator


__all__ = ["enforce_rate_limit", "rate_limit"]
