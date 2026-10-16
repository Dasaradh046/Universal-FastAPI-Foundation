"""
User agent parsing utilities for device tracking.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ParsedUserAgent:
    """Parsed user agent information."""

    device: str
    browser: str
    os: str


def parse_user_agent(user_agent: str | None) -> ParsedUserAgent:
    """Parse a User-Agent string into device/browser/os.

    Uses a simple heuristic-based parser. For production, consider integrating
    a library like `ua-parser` for more accurate parsing.
    """
    if not user_agent:
        return ParsedUserAgent(device="unknown", browser="unknown", os="unknown")

    ua_lower = user_agent.lower()

    # Browser detection
    if "edg" in ua_lower:
        browser = "Edge"
    elif "chrome" in ua_lower and "chromium" not in ua_lower:
        browser = "Chrome"
    elif "firefox" in ua_lower:
        browser = "Firefox"
    elif "safari" in ua_lower:
        browser = "Safari"
    elif "curl" in ua_lower:
        browser = "curl"
    else:
        browser = "Other"

    # OS detection
    if "windows" in ua_lower:
        os_name = "Windows"
    elif "mac os" in ua_lower:
        os_name = "macOS"
    elif "linux" in ua_lower:
        os_name = "Linux"
    elif "android" in ua_lower:
        os_name = "Android"
    elif "iphone" in ua_lower or "ipad" in ua_lower:
        os_name = "iOS"
    else:
        os_name = "Unknown"

    # Device type detection
    if "mobile" in ua_lower:
        device = "Mobile"
    elif "tablet" in ua_lower or "ipad" in ua_lower:
        device = "Tablet"
    else:
        device = "Desktop"

    return ParsedUserAgent(device=device, browser=browser, os=os_name)


def describe_client(user_agent: str | None) -> str:
    """Return a human-readable client description from a User-Agent string."""
    parsed = parse_user_agent(user_agent)
    return f"{parsed.browser} on {parsed.os} ({parsed.device})"


__all__ = ["ParsedUserAgent", "parse_user_agent", "describe_client"]
