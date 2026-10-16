"""
Cache abstraction with optional Redis adapter.

In production, configure ``REDIS_URL`` (e.g. ``redis://localhost:6379/0``)
to enable a shared cache backed by Redis. When no Redis URL is configured,
a no-op in-memory cache is used.
"""

from __future__ import annotations

from typing import Any

from app.core.config.settings import settings
from app.core.logging.logging import get_logger

logger = get_logger(__name__)

# In-memory fallback cache
_memory_cache: dict[str, Any] = {}


class Cache:
    """Simple cache abstraction with Redis or in-memory backend."""

    def __init__(self) -> None:
        self._redis: Any = None
        if settings:
            redis_url = getattr(settings, "REDIS_URL", None)
            if redis_url:
                try:
                    import redis.asyncio as redis

                    self._redis = redis.from_url(redis_url)
                    logger.info("Redis cache connected: %s", redis_url)
                except ImportError:
                    logger.warning("redis package not installed; using in-memory cache")
                except Exception as exc:
                    logger.warning("Redis connection failed; using in-memory cache: %s", exc)

    async def get(self, key: str) -> Any:
        """Get a value from the cache."""
        if self._redis:
            val = await self._redis.get(key)
            if val is not None:
                return val
            return None
        return _memory_cache.get(key)

    async def set(self, key: str, value: Any, expire: int | None = None) -> None:
        """Set a value in the cache with optional expiry (seconds)."""
        if self._redis:
            await self._redis.set(key, value, ex=expire)
        else:
            _memory_cache[key] = value

    async def delete(self, key: str) -> None:
        """Delete a key from the cache."""
        if self._redis:
            await self._redis.delete(key)
        else:
            _memory_cache.pop(key, None)


# Singleton instance
cache: Cache | None = None


def get_cache() -> Cache:
    """Get or create the cache singleton."""
    global cache
    if cache is None:
        cache = Cache()
    return cache


__all__ = ["Cache", "get_cache", "cache"]
