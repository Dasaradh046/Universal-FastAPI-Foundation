"""
Permissions for the notifications module.
"""

from __future__ import annotations

from app.core.permissions import Permission

NOTIFY_READ = Permission(
    code="notify:read",
    name="Read Notifications",
    description="View notifications and delivery status",
    module="notifications",
    action=None,
)

NOTIFY_WRITE = Permission(
    code="notify:write",
    name="Manage Notifications",
    description="Create, update, delete notifications and templates",
    module="notifications",
    action=None,
)

NOTIFY_SEND = Permission(
    code="notify:send",
    name="Send Notifications",
    description="Send notifications through configured channels",
    module="notifications",
    action=None,
)

NOTIFY_TEMPLATES = Permission(
    code="notify:templates",
    name="Manage Notification Templates",
    description="Create, update, delete notification templates",
    module="notifications",
    action=None,
)

__all__ = [
    "NOTIFY_READ",
    "NOTIFY_WRITE",
    "NOTIFY_SEND",
    "NOTIFY_TEMPLATES",
]
