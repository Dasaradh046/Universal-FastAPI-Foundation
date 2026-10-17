"""
Core package initialization.
"""
from __future__ import annotations

from app.core.interfaces import (
    IDatabaseService,
    IConfigurationService,
    ISecurityService,
    IAuthService,
    DatabaseService,
    ConfigurationService,
)

# Subpackages
from . import audit, cache, config, database, logging, middleware, security
from . import lifespan
# Bridge / compatibility modules (thin re-exports)
from . import dependencies, permissions, totp, user_agent, lockout, password_policy

__all__ = [
    # Interfaces
    "IDatabaseService",
    "IConfigurationService",
    "ISecurityService",
    "IAuthService",
    "DatabaseService",
    "ConfigurationService",
    # Subpackages
    "audit",
    "cache",
    "config",
    "database",
    "logging",
    "middleware",
    "security",
    "lifespan",
    # Bridge / compatibility modules
    "dependencies",
    "permissions",
    "totp",
    "user_agent",
    "lockout",
    "password_policy",
]