"""
User-agent bridge — re-exports parsing utilities from ``app.core.middleware.user_agent``.
"""
from __future__ import annotations

from app.core.middleware.user_agent import (
    ParsedUserAgent,
    parse_user_agent,
    describe_client,
)

__all__ = [
    "ParsedUserAgent",
    "parse_user_agent",
    "describe_client",
]
