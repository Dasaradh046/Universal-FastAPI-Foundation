"""
Example module API package.
"""

from __future__ import annotations

from app.modules.example_module.api.v1.routes import router as example_router

__all__ = ["example_router"]
