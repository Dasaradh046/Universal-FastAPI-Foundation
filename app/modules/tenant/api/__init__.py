"""
Tenant API package.
"""

from __future__ import annotations

from app.modules.tenant.api.v1.routes import router as tenant_router_v1

__all__ = ["tenant_router_v1"]
