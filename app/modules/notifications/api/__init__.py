"""
Notifications API package.
"""

from __future__ import annotations

from app.modules.notifications.api.v1.routes import router as notifications_router_v1

__all__ = ["notifications_router_v1"]
