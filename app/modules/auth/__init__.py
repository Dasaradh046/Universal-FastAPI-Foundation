"""
Auth module — authentication and session management.
"""

from app.modules.auth.services import AuthService, get_auth_service

__all__ = ["AuthService", "get_auth_service"]
