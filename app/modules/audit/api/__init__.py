"""
Audit API package.
"""

from __future__ import annotations

from app.modules.audit.api.v1.routes import router as audit_router_v1

__all__ = ["audit_router_v1"]
