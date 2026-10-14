"""
Email infrastructure — base message type and service abstraction.

This is the minimal email infrastructure needed by the auth module.
Provider-specific implementations live in ``app.integrations.email``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List

from pydantic import EmailStr


@dataclass
class EmailMessage:
    """Email message to be sent via a provider."""

    to: List[str]
    subject: str
    body: str
    html_body: str | None = None
    from_email: str | None = None
    cc: List[str] = field(default_factory=list)
    bcc: List[str] = field(default_factory=list)
    attachments: List = field(default_factory=list)


__all__ = ["EmailMessage"]
