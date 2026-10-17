"""
Auth API package.
"""

from __future__ import annotations

from app.modules.auth.api.v1.routes import router as auth_router_v1

__all__ = ["auth_router_v1"]
